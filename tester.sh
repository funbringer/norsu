#!/usr/bin/env bash

TEST_DIR=$(dirname $0)
export NORSU_PATH=$TEST_DIR/pg

handler() {
	rm -rf $NORSU_PATH
	exit 1
}

trap handler SIGINT

mkdir -p "$TEST_DIR/results"
rm -rf "$TEST_DIR/regression.diffs"

for t in $TEST_DIR/tests/*; do
	NAME="$(basename $t)"
	OUT="${NAME%.*}.out"

	EXPECTED="$TEST_DIR/expected/$OUT"
	RESULT="$TEST_DIR/results/$OUT"

	printf "Running test $NAME ... "
	bash "$t" > "$RESULT" 2>&1

	if [ -f "$EXPECTED" ]; then
		DIFF="$(diff -u "$EXPECTED" "$RESULT")"

		if [ "$DIFF" == "" ]; then
			echo OK
		else
			echo FAIL
			echo "$DIFF" >> "$TEST_DIR/regression.diffs"
		fi
	else
		echo
		printf "\tmissing output file $EXPECTED\n" >&2
	fi
done
