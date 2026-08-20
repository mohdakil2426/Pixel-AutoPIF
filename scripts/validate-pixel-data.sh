#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s <json-file>\n' "$0" >&2
  exit 2
fi

input=$1
if [[ ! -f $input ]]; then
  printf 'missing JSON file: %s\n' "$input" >&2
  exit 2
fi

command -v perl >/dev/null 2>&1 || {
  printf 'Perl with JSON::PP is required\n' >&2
  exit 2
}

perl - "$input" <<'PERL'
use strict;
use warnings;
use JSON::PP qw(decode_json);

my $path = shift @ARGV;
open my $fh, '<', $path or die "cannot read $path: $!\n";
local $/;
my $raw = <$fh>;
my $data = eval { decode_json($raw) };
die "invalid JSON: $@\n" if $@;
die "top-level JSON value must be a non-empty array\n"
    unless ref($data) eq 'ARRAY' && @$data;

my @required = sort qw(fingerprint securityPatch manufacturer model);
my $required_keys = join("\0", @required);

sub fail {
    my ($index, $message) = @_;
    die "entry[$index]: $message\n";
}

sub allowed_model {
    my ($model) = @_;
    return 1 if $model eq 'Pixel Fold' || $model eq 'Pixel Tablet';
    return 1 if $model =~ /\APixel ([0-9]+)/ && $1 >= 6;
    return 0;
}

sub valid_date {
    my ($value) = @_;
    return $value =~ /\A[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])\z/;
}
for my $index (0 .. $#$data) {
    my $item = $data->[$index];
    fail($index, 'value must be an object') unless ref($item) eq 'HASH';

    my @keys = sort keys %$item;
    fail($index, 'object must contain exactly the four required fields')
        unless join("\0", @keys) eq $required_keys;

    for my $key (@required) {
        fail($index, "$key must be a string")
            if ref($item->{$key}) ne '' || !defined($item->{$key});
        fail($index, "$key must not be blank")
            unless length $item->{$key};
    }

    fail($index, 'manufacturer must be Google')
        unless $item->{manufacturer} eq 'Google';
    fail($index, 'model is outside the Pixel 6+ policy')
        unless allowed_model($item->{model});
    fail($index, 'securityPatch must be a valid YYYY-MM-DD date')
        unless valid_date($item->{securityPatch});
    fail($index, 'fingerprint is not a CANARY release fingerprint')
        unless $item->{fingerprint} =~ /\Agoogle\/[a-z0-9_]+\/[a-z0-9_]+:CANARY\/[^\/\s]+\/[0-9]+:user\/release-keys\z/;
}

printf "validated %d canary entries\n", scalar @$data;
PERL
