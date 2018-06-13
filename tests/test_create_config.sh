set -v

export NORSU_PATH="$PWD/pg"

# run with default options
norsu status

# check files
if [ -e "$NORSU_PATH" ]; then echo OK; fi
if [ -e "$NORSU_PATH/.norsu" ]; then echo OK; fi
if [ -e "$NORSU_PATH/.norsu.toml" ]; then echo OK; fi

# check default config
cat "$NORSU_PATH/.norsu.toml"

# remove dir
rm -rf "$NORSU_PATH"
