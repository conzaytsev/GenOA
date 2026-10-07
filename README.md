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

For sequence optimisation, there are several parameters to choose. Toggling the switch on a parameter adds it to the optimisation algorithm. Each parameter has a target value, that the algorithm is trying to achieve and the `Parameter weight` option, that by default is set to 1, but can be changed to any non-zero value. This value affects the influence of a specific parameter compared to the others. Therefore increasing it for one of the parameters increases the optimisation accuracy for that parameter to the detriment of the others. As some of the potential parameter combinations could not theoretically be achieved, setting parameter weights allows to set priorities. Setting the parameter to zero disables it and is practically the same as turning the switch off.

The `Excluded sites` option allows to set a list of oligonucleotides to be avoided in the optimised sequence.

`Advanced settings` contains internal setting of the optimisation algorithm, that is based on the genetic algorithm.
