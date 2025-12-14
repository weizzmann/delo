# scripts/mv-dist.sh (в корне репо)
set -e
SRC="backend/app/dist-tmp"
TPL="backend/app/templates"
ST="backend/app/static"

mkdir -p "$TPL" "$ST"
# index.html -> templates
mv "$SRC/index.html" "$TPL/index.html"
# остальное -> static
rsync -a --remove-source-files "$SRC/" "$ST/"
rmdir "$SRC" || true
