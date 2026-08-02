#!/usr/bin/env bash
set -Eeuo pipefail

json_file=${1:?usage: scripts/pixel-data-metrics.sh data/pif-data.json}

if [[ ! -f $json_file ]]; then
  printf '0\tNone\t-\t-\n'
  exit 0
fi

perl -MJSON::PP -0777 - "$json_file" <<'PERL'
use strict;
use warnings;
use JSON::PP;

my ($path) = @ARGV;
open my $fh, '<', $path or do { print "0\tNone\t-\t-\n"; exit 0; };
local $/;
my $data = eval { decode_json(<$fh>) };
if (!$data || ref($data) ne 'ARRAY') {
    print "0\tNone\t-\t-\n";
    exit 0;
}
my @models = map { $_->{model} // '' } grep { ref($_) eq 'HASH' } @$data;
my @patches = sort grep { defined($_) && /^\d{4}-\d{2}-\d{2}$/ }
    map { $_->{securityPatch} } grep { ref($_) eq 'HASH' } @$data;
print scalar(@$data), "\t", (join(', ', @models) || 'None'), "\t",
    ($patches[0] // '-'), "\t", ($patches[-1] // '-'), "\n";
PERL
