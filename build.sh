#!/bin/sh

tmpdir=$(mktemp -d) || exit 1
pushd "${tmpdir}"
for package in antiqua arial classico garamond grotesq lettergothic; do
	wget "https://mirrors.ctan.org/fonts/urw/${package}.zip"
	unzip "${package}.zip"
done
mv antiqua/doc/uaqr8ac.afm.org antiqua/fonts/uaqr8ac.afm
mv grotesq/ugqb8a.afm.org grotesq/ugqb8a.afm
popd

fontforge -script convert.py -o dist "${tmpdir}/antiqua/fonts"
fontforge -script convert.py -o dist "${tmpdir}/arial/type1"
fontforge -script convert.py -o dist "${tmpdir}/classico/opentype"
fontforge -script convert.py -o dist "${tmpdir}/garamond"
fontforge -script convert.py -o dist "${tmpdir}/grotesq"
fontforge -script convert.py -o dist "${tmpdir}/lettergothic"

rm -rf "${tmpdir}"

exit 0
