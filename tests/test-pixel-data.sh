#!/usr/bin/env bash
set -Eeuo pipefail

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

bash -n scripts/crawl-pixel-data.sh scripts/validate-pixel-data.sh scripts/pixel-data-metrics.sh tests/test-pixel-data.sh
scripts/validate-pixel-data.sh tests/fixtures/pif-pixel-data.json
metrics=$(scripts/pixel-data-metrics.sh tests/fixtures/pif-pixel-data.json)
[[ $metrics == $'1\tPixel 8a\t2026-07-05\t2026-07-05' ]] || {
  printf 'unexpected Pixel data metrics: %s\n' "$metrics" >&2
  exit 1
}

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

perl -MJSON::PP - tests/fixtures/pif-pixel-data.json "$tmpdir/pixel5.json" <<'PERL'
use strict;
use warnings;
use JSON::PP;

my ($input, $output) = @ARGV;
open my $in, '<', $input or die "cannot read $input: $!\n";
local $/;
my $data = decode_json(<$in>);
$data->[0]{model} = 'Pixel 5';
open my $out, '>', $output or die "cannot write $output: $!\n";
print {$out} JSON::PP->new->canonical(1)->pretty(1)->encode($data);
PERL

if scripts/validate-pixel-data.sh "$tmpdir/pixel5.json"; then
  printf '%s\n' 'Pixel 5 fixture was incorrectly accepted' >&2
  exit 1
fi

perl -MJSON::PP - tests/fixtures/pif-pixel-data.json "$tmpdir/extra-key.json" <<'PERL'
use strict;
use warnings;
use JSON::PP;

my ($input, $output) = @ARGV;
open my $in, '<', $input or die "cannot read $input: $!\n";
local $/;
my $data = decode_json(<$in>);
$data->[0]{extra} = 'rejected';
open my $out, '>', $output or die "cannot write $output: $!\n";
print {$out} JSON::PP->new->canonical(1)->pretty(1)->encode($data);
PERL

if scripts/validate-pixel-data.sh "$tmpdir/extra-key.json"; then
  printf '%s\n' 'extra-key fixture was incorrectly accepted' >&2
  exit 1
fi

printf '%s\n' 'Pixel data shell checks passed'
