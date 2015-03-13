#!/bin/sh -e


extract_vars() {
        sed -re '/^\+.*%.*/ s/.*%([^%]+)%.*/\L\1/;tx;d;:x' neutron-upgrade.patch
}

convert_vars_to_regex() {
        tr "\n" " "| sed -re 's,^,^(,;s,.$,),;s, ,|,g'
}

generate_template_regex() {
        find /etc/neutron -type f | xargs -I{} egrep "`extract_vars | convert_vars_to_regex`" {}  | awk -F= '{key = gensub(" ", "", "g", $1); printf("s|%%%s%%|%s|g;", toupper(key), $2)}'
}


sed -r "`generate_template_regex`"  neutron-upgrade.patch
