#!/usr/bin/env bash
set -Eeuo pipefail

json_file=${1:?usage: scripts/pixel-data-metrics.sh pif.json}

if [[ ! -f $json_file ]]; then
  printf '0\tNone\t-\t-\n'
  exit 0
fi

perl -MJSON::PP - "$json_file" <<'PERL'
use strict;
use warnings;
my $raw = do { local (@ARGV, $/) = shift; <> };
my $data = eval { JSON::PP::decode_json($raw) };
if (!$data || ref($data) ne 'ARRAY') {
    print "0\tNone\t-\t-\n";
    exit 0;
}
my @models = map { $_->{model} // '' } grep { ref($_) eq 'HASH' } @$data;
my @patches = sort grep { defined($_) && /^\d{4}-\d{2}-\d{2}$/ }
    map { $_->{securityPatch} } grep { ref($_) eq 'HASH' } @$data;
printf "%d\t%s\t%s\t%s\n", scalar(@$data), join(', ', @models) || 'None', $patches[0] // '-', $patches[-1] // '-';
PERL
