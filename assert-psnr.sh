#!/bin/bash

INPUT=$1
REFERENCE=$2
PSNR_LIMIT=$3

MEAN_PSNR="$(ffmpeg -i $INPUT -i $REFERENCE \
                    -lavfi '[0:v]format=gbrp14,setpts=N[out0];[1:v]format=gbrp14,setpts=N[out1];[out0][out1]psnr' \
                    -f null - 2>&1 | \
  grep average |                                                      \
  tail -n 1 |                                                         \
  sed -rn 's/.*average:(([[:digit:].]+)|inf).*/\1/p')"

if [ $? -ne 0 ];
then
    echo "ERROR: error generating PSNR for intermediate videos"
    exit -1
fi

IS_VALID=0
if [ "$MEAN_PSNR" = "inf" ];
then
    IS_VALID=1
elif [ "$MEAN_PSNR" = "" ];
then
    IS_VALID=0
    MEAN_PSNR="[NaN]"
else
    IS_VALID=$(bc <<< "$MEAN_PSNR >= $PSNR_LIMIT")
fi

if [ $? -ne 0 ];
then
    echo "ERROR: unable to compare PSNRs"
    exit -1
elif [ $IS_VALID -eq 0 ];
then
    echo "FAIL: calculated PSNR $MEAN_PSNR below limit of $PSNR_LIMIT"
    exit -1
else
    echo "PASS: PSNR $MEAN_PSNR"
fi