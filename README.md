# GenOA
Gene Optimisation Assistant

This tool can be used for nucleotide sequence analysis and codon optimisation for the desired expression levels and species of interest.
Optimisation can be performed using any combination of parameters including: predicted expression level, codon bias, GC content and codon usage irregularity.

## Download
Compiled versions for MacOS and Windows are available in the Releases

## Usage
The tool comes with pre-trained models for E. coli. We plan to add more species with lated development.
For other species there is the `Custom` option in the `Model organism selection` tab, which opens additional menus to upload datasets for CEI and GeneSpace model training. More about dataset formats can be seen in the readme for those projects.

There are two options for the input sequence: nucleotide (DNA) and protein. Both of them can be used for sequence optimisation, but nucleotide sequences also can be analysed for the target species using the `Calculate sequence features` option. This shows the calculated parameters with the option to show some of them on a graph compared to the distibution for the native genes.
