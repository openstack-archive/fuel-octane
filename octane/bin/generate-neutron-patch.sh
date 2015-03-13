#!/bin/sh -e

PATCH=${1-"../patches/neutron-upgrade.patch"}

if [ ! -f "$PATCH" ]; then
    echo "Usage $0 neutron-upgrade.patch > neutron-upgrade-rendered.patch" >> /dev/stderr
    exit 1
fi



extract_vars() {
        sed -re '/^\+.*%.*/ s/.*%([^%]+)%.*/\L\1/;tx;d;:x' $PATCH
}

convert_vars_to_regex() {
        tr "\n" " "| sed -re 's,^,^(,;s,.$,),;s, ,|,g'
}

generate_template_regex() {
        find /etc/neutron -type f | xargs -I{} egrep "`extract_vars | convert_vars_to_regex`" {}  | awk -F= '{key = gensub(" ", "", "g", $1); printf("s|%%%s%%|%s|g;", toupper(key), $2)}'
}


sed -r "`generate_template_regex`" ${PATCH}
