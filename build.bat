@echo off
docker build -t opr-builder .
docker run --rm -v %cd%:/output opr-builder cp /app/dist/OPRDatacard /output/
echo Linux executable created: .\OPRDatacard