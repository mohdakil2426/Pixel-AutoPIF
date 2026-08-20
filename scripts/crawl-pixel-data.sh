#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
usage: scripts/crawl-pixel-data.sh [--output pif.json]
USAGE
}

output=pif.json
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      [[ $# -ge 2 ]] || { printf '%s\n' '--output requires a path' >&2; exit 2; }
      output=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done


script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
case "$output" in
  /*) ;;
  *) output="$repo_root/$output" ;;
esac
mkdir -p "$(dirname -- "$output")"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

ANDROID_VERSIONS_URL=https://developer.android.com/about/versions
FACTORY_IMAGES_URL=https://developers.google.com/android/images
FLASH_HOME=https://flash.android.com
FLASH_API=https://content-flashstation-pa.googleapis.com/v1/builds
PIXEL_BULLETIN=https://source.android.com/docs/security/bulletin/pixel
USER_AGENT='Pixel-AutoPIF/1.0'
download() {
  local url=$1
  local destination=$2
  curl --fail --silent --show-error --location --retry 2 --retry-all-errors \
    --connect-timeout 15 --max-time 45 --compressed \
    --user-agent "$USER_AGENT" "$url" -o "$destination"
}

absolute_developer_url() {
  local link=$1
  case "$link" in
    https://*) printf '%s\n' "$link" ;;
    /*) printf 'https://developer.android.com%s\n' "$link" ;;
    *) printf 'https://developer.android.com/%s\n' "$link" ;;
  esac
}

supported_model() {
  local model=$1
  case "$model" in
    'Pixel Fold'|'Pixel Tablet') return 0 ;;
  esac
  if [[ $model =~ ^Pixel[[:space:]]+([0-9]+) ]]; then
    local number=${BASH_REMATCH[1]}
    number=$((10#$number))
    (( number >= 6 ))
    return
  fi
  return 1
}

clean_model() {
  printf '%s' "$1" |
    sed -E 's/<[^>]+>/ /g; s/[[:space:]]+/ /g; s/^ //; s/ $//'
}

printf '%s\n' 'Fetching current Android release index...'
versions_html="$tmpdir/versions.html"
download "$ANDROID_VERSIONS_URL" "$versions_html"

latest_url=$(
  grep -oE 'https://developer.android.com/about/versions/[0-9]+[^"[:space:]]*' "$versions_html" |
    sed -E 's/[?#].*$//' |
    sort -Vu |
    tail -n 1 || true
)
if [[ -z $latest_url ]]; then
  latest_path=$(
    grep -oE 'href="/about/versions/[0-9]+[^"]*"' "$versions_html" |
      sed -E 's/^href="([^"]*)".*$/\1/' |
      sed -E 's/[?#].*$//' |
      sort -Vu |
      tail -n 1 || true
  )
  [[ -n $latest_path ]] || {
    printf '%s\n' 'could not determine the latest Android release URL' >&2
    exit 1
  }
  latest_url=$(absolute_developer_url "$latest_path")
fi

latest_html="$tmpdir/latest.html"
download "$latest_url" "$latest_html"

download_hrefs=$(
  grep -oE 'href="[^"]*download[^"]*"' "$latest_html" |
    sed -E 's/^href="([^"]*)".*$/\1/' || true
)
fi_link=$(
  printf '%s\n' "$download_hrefs" |
    grep -i qpr |
    grep -vi 'download-ota' |
    head -n 1 || true
)
ota_link=$(
  printf '%s\n' "$download_hrefs" |
    grep -i qpr |
    grep -i 'download-ota' |
    head -n 1 || true
)
if [[ -z $fi_link || -z $ota_link ]]; then
  fi_link=$(
    printf '%s\n' "$download_hrefs" |
      grep -vi 'download-ota' |
      head -n 1 || true
  )
  ota_link=$(
    printf '%s\n' "$download_hrefs" |
      grep -i 'download-ota' |
      head -n 1 || true
  )
fi
[[ -n $fi_link && -n $ota_link ]] || {
  printf '%s\n' 'could not determine full-image and OTA table URLs' >&2
  exit 1
}
fi_html="$tmpdir/factory-images.html"
ota_html="$tmpdir/ota-images.html"
download "$(absolute_developer_url "$fi_link")" "$fi_html" || true
download "$(absolute_developer_url "$ota_link")" "$ota_html" || true

fi_rows=$(grep -c 'tr id=' "$fi_html" 2>/dev/null || true)
ota_rows=$(grep -c 'tr id=' "$ota_html" 2>/dev/null || true)
source_html=$fi_html
if (( ota_rows > fi_rows )); then
  source_html=$ota_html
fi

google_factory_html="$tmpdir/google-factory-images.html"
curl --fail --silent --show-error --location --retry 2 --retry-all-errors \
  --connect-timeout 15 --max-time 45 --compressed \
  --cookie "devsite_wall_acks=nexus-image-tos" \
  --user-agent "$USER_AGENT" "$FACTORY_IMAGES_URL" -o "$google_factory_html" || true

devices_tsv="$tmpdir/devices.tsv"
perl - "$source_html" "$google_factory_html" "$devices_tsv" <<'PERL'
use strict;
use warnings;
my ($source_path, $factory_path, $out_path) = @ARGV;

my %devices; # product => { model => $model, release_id => $id, incremental => $num }

if (-f $source_path) {
    open my $in, '<', $source_path or warn "cannot read $source_path: $!\n";
    if ($in) {
        local $/;
        my $html = <$in>;
        while ($html =~ /<tr[^>]*id="([^"]+)"[^>]*>\s*<td>(.*?)<\/td>/sg) {
            my $prod = $1;
            my $model = $2;
            $model =~ s/<[^>]+>/ /g; $model =~ s/\s+/ /g; $model =~ s/^\s+|\s+$//g;
            $prod = "${prod}_beta" unless $prod =~ /_beta$/;
            $devices{$prod} = { model => $model, release_id => '', incremental => '' };
        }
    }
}

if (-f $factory_path) {
    open my $in, '<', $factory_path or warn "cannot read $factory_path: $!\n";
    if ($in) {
        local $/;
        my $html = <$in>;
        while ($html =~ /<h2\s+id="([^"]+)"[^>]*>(.*?)<\/h2>(.*?)(?=<h2|\z)/sg) {
            my $device = $1;
            my $heading = $2;
            my $section = $3;
            $heading =~ s/<[^>]+>//g;
            my ($model) = $heading =~ /for\s+(Pixel[^"<]+)/;
            next unless $model;
            $model =~ s/^\s+|\s+$//g;
            my $prod = "${device}_beta";

            my @rows = $section =~ /<tr[^>]*id="[^"]*"[^>]*>(.*?)<\/tr>/sg;
            next unless @rows;
            my $last_row = $rows[-1];
            my ($version) = $last_row =~ /<td>(.*?)<\/td>/s;
            $version =~ s/<[^>]+>//g; $version =~ s/^\s+|\s+$//g;
            my ($flash_build) = $last_row =~ /flash\.android\.com\/build\/([0-9]+)\?target=/;
            my ($release_id) = $version =~ /\(([^,\)]+)/;
            $release_id =~ s/^\s+|\s+$//g if $release_id;
            $flash_build //= '';
            $release_id //= '';

            if (!exists $devices{$prod}) {
                $devices{$prod} = { model => $model, release_id => $release_id, incremental => $flash_build };
            } elsif ($release_id && !$devices{$prod}{release_id}) {
                $devices{$prod}{release_id} = $release_id;
                $devices{$prod}{incremental} = $flash_build;
            }
        }
    }
}

open my $out, '>', $out_path or die "cannot write $out_path: $!\n";
for my $prod (sort keys %devices) {
    my $info = $devices{$prod};
    print {$out} join("\t", $info->{model}, $prod, $info->{release_id} || '', $info->{incremental} || ''), "\n";
}
PERL
flash_html="$tmpdir/flash.html"
download "$FLASH_HOME" "$flash_html"
flash_key=$(grep -oE 'AIza[[:alnum:]_-]{20,}' "$flash_html" | head -n 1 || true)
[[ -n $flash_key ]] || {
  printf '%s\n' 'could not extract Flash Station API key' >&2
  exit 1
}

bulletin_html="$tmpdir/pixel-bulletin.html"
download "$PIXEL_BULLETIN" "$bulletin_html"

entries_tsv="$tmpdir/entries.tsv"
: > "$entries_tsv"
entry_count=0

while IFS=$'\t' read -r raw_model product fb_release_id fb_incremental; do
  [[ -n $raw_model && -n $product ]] || continue
  model=$(clean_model "$raw_model")
  supported_model "$model" || continue
  [[ $product == *_beta ]] || product="$product"_beta
  device=$(printf '%s' "$product" | sed 's/_beta$//')

  printf 'Crawling %s (%s)...\n' "$model" "$product"
  station_json="$tmpdir/station-$entry_count.json"
  reversed_json="$tmpdir/reversed-$entry_count.json"
  release_json="$tmpdir/release-$entry_count.json"
  canary_found=0
  if curl --fail --silent --show-error --location --retry 2 --retry-all-errors \
    --connect-timeout 15 --max-time 45 --compressed \
    --user-agent "$USER_AGENT" --header "Referer: $FLASH_HOME" \
    "$FLASH_API?product=$product&key=$flash_key" -o "$station_json" 2>/dev/null; then
    tac "$station_json" > "$reversed_json" 2>/dev/null || true
    if grep -m 1 -A 20 '"canary": true' "$reversed_json" > "$release_json" 2>/dev/null; then
      canary_found=1
    fi
  fi

  release_id=
  incremental=
  release_suffix=
  if (( canary_found == 1 )); then
    release_id=$(
      grep -m 1 '"releaseCandidateName"' "$release_json" |
        sed -nE 's/.*"releaseCandidateName"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/p'
    )
    incremental=$(
      grep -m 1 '"buildId"' "$release_json" |
        sed -nE 's/.*"buildId"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/p'
    )
    release_suffix=$(
      grep -m 1 '"id"' "$release_json" |
        sed -nE 's/.*"id"[[:space:]]*:[[:space:]]*"canary-([^"]+)".*/\1/p'
    )
  elif [[ -n $fb_release_id && -n $fb_incremental ]]; then
    printf 'using factory image release %s (%s) for %s\n' "$fb_release_id" "$fb_incremental" "$product" >&2
    release_id="$fb_release_id"
    incremental="$fb_incremental"
    # Derive release_suffix from release_id date (e.g. CD1A.260714.001.A9 -> 260714 -> 20260714)
    if [[ $release_id =~ \.([0-9]{2})([0-9]{2})([0-9]{2})\. ]]; then
      release_suffix="20${BASH_REMATCH[1]}${BASH_REMATCH[2]}${BASH_REMATCH[3]}"
    fi
  fi

  [[ -n $release_id && -n $incremental ]] || {
    printf 'missing release data for %s\n' "$product" >&2
    exit 1
  }

  fingerprint="google/$product/$device:CANARY/$release_id/$incremental:user/release-keys"
  bulletin_month=
  if [[ -n $release_suffix ]]; then
    bulletin_month=$(printf '%s' "$release_suffix" | sed -nE 's/^([0-9]{4})([0-9]{2}).*$/\1-\2/p')
  fi
  security_patch=
  if [[ -n $bulletin_month ]]; then
    security_patch=$(
      grep -oE "<td>$bulletin_month-[0-9]{2}</td>" "$bulletin_html" |
        sed -nE 's/.*<td>([^<]+)<\/td>.*/\1/p' |
        head -n 1 || true
    )
  fi
  if [[ -z $security_patch ]]; then
    fallback_day=05
    if [[ -n $release_suffix ]]; then
      fallback_day=$(printf '%s' "$release_suffix" | sed -nE 's/^[0-9]{6}([0-9]{2}).*$/\1/p')
      [[ -n $fallback_day ]] || fallback_day=05
    fi
    [[ -n $bulletin_month ]] || {
      printf 'could not derive a release patch month for %s\n' "$product" >&2
      exit 1
    }
    security_patch="$bulletin_month-$fallback_day"
    printf 'using release-derived patch %s for %s\n' "$security_patch" "$product" >&2
  fi

  printf '%s\t%s\tGoogle\t%s\n' "$fingerprint" "$security_patch" "$model" >> "$entries_tsv"
  entry_count=$((entry_count + 1))
done < "$devices_tsv"

(( entry_count > 0 )) || {
  printf '%s\n' 'the crawl returned no Pixel 6+ entries' >&2
  exit 1
}

candidate_output="$tmpdir/pif.json"
perl - "$entries_tsv" "$candidate_output" <<'PERL'
use strict;
use warnings;
use JSON::PP;

my ($input, $output) = @ARGV;
open my $in, '<', $input or die "cannot read $input: $!\n";
my @entries;
while (my $line = <$in>) {
    chomp $line;
    next unless length $line;
    my @parts = split /\t/, $line, -1;
    die "invalid crawler row\n" unless @parts == 4;
    push @entries, {
        fingerprint => $parts[0],
        securityPatch => $parts[1],
        manufacturer => $parts[2],
        model => $parts[3],
    };
}
die "crawler produced no entries\n" unless @entries;
open my $out, '>', $output or die "cannot write $output: $!\n";
print {$out} JSON::PP->new->canonical(1)->pretty(1)->encode(\@entries);
PERL

"$script_dir/validate-pixel-data.sh" "$candidate_output"
mv "$candidate_output" "$output"
printf 'wrote %d entries to %s\n' "$entry_count" "$output"
