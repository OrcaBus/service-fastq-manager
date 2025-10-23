#!/usr/bin/env bash

set -euo pipefail

: '
Performs the following tasks

Given a list of gzip compressed fastq files,

Set up
1. Download reference fasta
2. Download sites vcf
3. Create bedtools slop around sites file
4. Generate reference fasta from bedtools slop
5. Generate minimap2 index from mini reference fasta

Run
1. Stream the input files into minimap2, we may use orad for this if the file ends with ".ora"
2. Write the bam file to disk, omitting unmapped reads
3. Sort and index the bam file
4. Upload the bam and bai files to S3 to the fingerprinting bucket
'
