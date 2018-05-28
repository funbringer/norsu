#!/usr/bin/env bash

TEST_DIR=$(dirname $0)
export NORSU_PATH=$TEST_DIR/pg


handler() {
	rm -rf $NORSU_PATH
	exit 1
}

trap handler SIGINT


# prepare files and dirs
mkdir -p "$TEST_DIR/results"
rm -rf "$TEST_DIR/regression.diffs"


if [ -t 1 ]; then
	RED="\033[31m"
	GREEN="\033[32m"
	YELLOW="\033[33m"
	RESET="\033[0m"
else
	RED=
	GREEN=
	YELLOW=
	RESET=
fi


TESTS_TOTAL=0
TESTS_GOOD=0
TESTS_BAD=0

echo "Norsu tester"

echo
printf $YELLOW"===== Tests: ====="$RESET"\n"
echo

for t in "$TEST_DIR"/tests/*; do
	NAME="$(basename $t)"
	OUT="${NAME%.*}.out"

	EXPECTED="$TEST_DIR/expected/$OUT"
	RESULT="$TEST_DIR/results/$OUT"

	printf "Running test $NAME ... "
	bash "$t" > "$RESULT" 2>&1

	TESTS_TOTAL=$((TESTS_TOTAL + 1))

	if [ -f "$EXPECTED" ]; then
		DIFF="$(diff -u "$EXPECTED" "$RESULT")"

		if [ "$DIFF" == "" ]; then
			printf $GREEN"OK"$RESET"\n"
			TESTS_GOOD=$((TESTS_GOOD + 1))
		else
			printf $RED"FAIL"$RESET"\n"
			TESTS_BAD=$((TESTS_BAD + 1))

			# append diff to regression report
			echo "$DIFF" >> "$TEST_DIR/regression.diffs"
		fi
	else
		echo
		printf "\tmissing output file $EXPECTED\n" >&2
	fi
done

# show report, if any
if [ -f regression.diffs ]; then
	echo
	printf $YELLOW"===== Diffs: ====="$RESET"\n"
	echo
	cat regression.diffs
fi

echo
printf $YELLOW"===== Summary: ====="$RESET"\n"
echo

echo "Total:  $TESTS_TOTAL"
echo "Passed: $TESTS_GOOD"
echo "Failed: $TESTS_BAD"
echo

# report errors using non-zero exit code
if [ "$TESTS_GOOD" -lt "$TESTS_TOTAL" ]; then
	exit 1
fi
