#!/bin/sh
# Rebuild the site from the clean ROM and push gh-pages (taint must pass first).
#   sh tools/publish.sh "message"
set -e
W=/d/n64work/banjotooie
ROM=$W/build/bt_clean.z64
RETAIL="$W/rom/Banjo-Tooie (USA).z64"
EJS=C:/Users/andre/n64work/mk64/emu
REPO=andrewnakas/banjotooie-cleanroom
cd /d/n64work/banjotooie-cleanroom
# the taint scan always runs on the exact ROM being published; any failing run aborts the publish
python -m games.banjotooie.taint_report "$RETAIL" $ROM > $W/build/taint.log 2>&1 || { tail -5 $W/build/taint.log; echo "TAINT FAILED: not publishing"; exit 1; }
tail -1 $W/build/taint.log
grep -q "FAILING (>= 32 B run): 0$" $W/build/taint.log || { echo "taint summary missing: not publishing"; exit 1; }
python ports/ejs/patch_core.py $ROM $EJS/cores_orig $W/emu/cores | tail -1
if [ ! -d $W/site/.git ]; then
  mkdir -p $W/site && cd $W/site && git init -q && git remote add origin https://github.com/$REPO.git
  cd /d/n64work/banjotooie-cleanroom
fi
python ports/ejs/make_site.py $ROM $EJS/ejs $W/site
cp $W/emu/cores/*.data $W/site/data/cores/
# one orphan commit per deploy: the Pages builder chokes on a long history of 32 MB ROMs
cd $W/site && git checkout -q --orphan tmp && git add -A && git commit -qm "Site: ${1:-rebuild}" \
  && { git branch -D gh-pages -q 2>/dev/null || true; } && git branch -m gh-pages
git config http.postBuffer 157286400
# the 32 MB push sometimes times out (HTTP 408): retry, then check the remote really has this commit
for i in 1 2 3; do git push -q -f origin gh-pages && break; echo "push failed, retry $i"; sleep 20; done
git ls-remote origin gh-pages | grep -q $(git rev-parse HEAD) || { echo "PUSH FAILED"; exit 1; }
git gc -q --prune=now && echo "pushed gh-pages"
gh api -X POST repos/$REPO/pages/builds -q .status 2>/dev/null || true
