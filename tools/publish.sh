#!/bin/sh
# Rebuild the site from the clean ROM and push gh-pages (taint must pass first).
#   sh tools/publish.sh "message"      (SKIP_TAINT=1 only if the taint report just ran on this exact ROM)
set -e
W=/d/n64work/banjotooie
ROM=$W/build/bt_clean.z64
RETAIL="$W/rom/Banjo-Tooie (USA).z64"
EJS=C:/Users/andre/n64work/mk64/emu
REPO=andrewnakas/banjotooie-cleanroom
cd /d/n64work/banjotooie-cleanroom
if [ -z "$SKIP_TAINT" ]; then
  python -m games.banjotooie.taint_report "$RETAIL" $ROM | tail -3
fi
python ports/ejs/patch_core.py $ROM $EJS/cores_orig $W/emu/cores | tail -1
if [ ! -d $W/site/.git ]; then
  mkdir -p $W/site && cd $W/site && git init -q && git remote add origin https://github.com/$REPO.git
  cd /d/n64work/banjotooie-cleanroom
fi
python ports/ejs/make_site.py $ROM $EJS/ejs $W/site
cp $W/emu/cores/*.data $W/site/data/cores/
# one orphan commit per deploy: the Pages builder chokes on a long history of 32 MB ROMs
cd $W/site && git checkout -q --orphan tmp && git add -A && git commit -qm "Site: ${1:-rebuild}" \
  && { git branch -D gh-pages -q 2>/dev/null || true; } && git branch -m gh-pages && git push -q -f origin gh-pages \
  && git gc -q --prune=now && echo "pushed gh-pages"
gh api -X POST repos/$REPO/pages/builds -q .status 2>/dev/null || true
