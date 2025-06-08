#!/bin/bash
docker build -t opr-builder .
docker run --rm -v "$(pwd)":/output opr-builder cp /app/dist/OPRDatacard /output/
chmod +x OPRDatacard
echo "Linux executable created: ./OPRDatacard"