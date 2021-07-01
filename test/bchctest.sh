#!/bin/bash

RUN="../bchc ../examples/simple.bch"
[ `$RUN` == "76a91470838296095e901677d7712339962fe7d9783c1688ac" ] || echo "test $RUN failed"

RUN="../bchc ../examples/test.bch"
[ `$RUN` == "a9140185cf618fdc6ef30dae87d8ee031f6479c781fb87" ] || echo "test $RUN failed"

RUN="../bchc --display out0 ../examples/math.bch"
[ `$RUN` == "515c9552985683" ] || echo "test $RUN failed"

RUN="../bchc --display out1 ../examples/math.bch"
[ `$RUN` == "5199568304123456788184" ] || echo "test $RUN failed"

RUN="../bchc -I../examples --hex testOpless.bch"
RESULT=$(($RUN) 2>&1)
RESULT=$(echo $RESULT | tr -d '\n')
[ "$RESULT" == "_\$timeInSec_b17576a9_\$address_88ac" ] || echo "test $RUN failed with $RESULT"

RUN="../bchc badLib.bch"
RESULT=$(($RUN) 2>&1)
RESULT=$(echo $RESULT | grep -o "badSymbol is not a statement" | wc -l)
[ "$RESULT" == "1" ] || echo "test $RUN failed with $RESULT"

RUN="../bchc badScript.bch"
RESULT=$(($RUN) 2>&1)
RESULT1=$(echo $RESULT | grep -o "badLib.bch" | wc -l)
RESULT2=$(echo $RESULT | grep -o "undefined symbol" | wc -l)
[[ "$RESULT1" > "0"  && "$RESULT2" > "0" ]] || echo "test $RUN failed with $RESULT"

RUN="../bchc testTemplate.bch"
RESULT=$(($RUN) 2>&1)
RESULT=$(echo $RESULT | tr -d '\n')
[ "$RESULT" == "76a9_\$addr_88ac" ] || echo "test $RUN failed with $RESULT"


RUN="../bchc --display badthing ../examples/math.bch"
RESULT=$(($RUN) 2>&1)
RESULT=$(echo $RESULT | tr -d '\n')
[ "$RESULT" == "Error: script must include a 'badthing' scriptify! command" ] || echo "test $RUN failed"


exit 0
