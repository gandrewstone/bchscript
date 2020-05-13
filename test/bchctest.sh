#!/bin/bash

RUN="../bchc ../examples/simple.bch"
[ `$RUN` == "_@sig__@pubkey_76a91470838296095e901677d7712339962fe7d9783c1688ac" ] || echo "test $RUN failed"

RUN="../bchc ../examples/test.bch"
[ `$RUN` == "a9140185cf618fdc6ef30dae87d8ee031f6479c781fb87" ] || echo "test $RUN failed"

RUN="../bchc --display out0 ../examples/math.bch"
[ `$RUN` == "515c9552985683" ] || echo "test $RUN failed"

RUN="../bchc --display out1 ../examples/math.bch"
[ `$RUN` == "5199568304123456788184" ] || echo "test $RUN failed"

RUN="../bchc testTemplate.bch"
RESULT=$(($RUN) 2>&1)
RESULT=$(echo $RESULT | tr -d '\n')
[ $RESULT == "_@sig__@pubkey_76a9_\$addr_88ac" ] || echo "test $RUN failed with $RESULT"


RUN="../bchc --display badthing ../examples/math.bch"
RESULT=$(($RUN) 2>&1)
RESULT=$(echo $RESULT | tr -d '\n')
[ "$RESULT" == "Error: script must include a 'badthing' scriptify! command" ] || echo "test $RUN failed"


exit 0
