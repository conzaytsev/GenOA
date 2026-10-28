from sklearn.svm import OneClassSVM, LinearSVC
from sklearn.metrics import accuracy_score
from math import sqrt
from numpy import sign, linalg, array
from random import shuffle


def coordinates(distribution):
    values = list(distribution.values())
    norm = sum(values)
    for i in range(len(values)):
        values[i] *= 1 / norm
    return values


def hyperplane_distance(hyperplane, point):
    result = 0 + hyperplane[0][0]
    norm = 0
    for i in range(len(hyperplane[1])):
        result += hyperplane[1][i] * point[i]
        norm += hyperplane[1][i] ** 2
    result /= sqrt(norm)
    return result


def nucleotide_distribution(sequence):
    distribution = {nucleotide: 0 for nucleotide in nucleotides}
    for j in range(0, len(sequence)):
        distribution[sequence[j]] += 1
    return distribution


def triplet_distribution(sequence):
    distribution = {triplet: 0 for triplet in triplets}
    for j in range(0, len(sequence), 3):
        if sequence[j: j + 3] in triplets:
            distribution[sequence[j: j + 3]] += 1
    return distribution


def sixplet_distribution(sequence):
    distribution = {sixplet: 0 for sixplet in sixplets}
    for j in range(0, len(sequence) - 3, 3):
        if sequence[j: j + 6] in sixplets:
            distribution[sequence[j: j + 6]] += 1
    return distribution


def read_file(filename):
    genes = []

    if filename.split('.')[-1] == 'csv':
        with open(filename, 'r') as file:
            data = file.readlines()
        for i in range(len(data)):
            if i > 0:
                data_string = data[i].replace('\n', '').split(';')
                genes.append(data_string[2])

    elif filename.split('.')[-1] == 'txt':
        with open(filename, 'r') as file:
            for line in file:
                if len(line[:-1]) % 3 == 0 and len(line[:-1]) == line.count('A') + line.count('T') + line.count(
                        'G') + line.count('C'):
                    genes.append(line[:-1])

    else:
        gene = ''
        with open(filename, 'r') as file:
            for line in file:
                if line[0] == '>':
                    if gene != '' and len(gene) % 3 == 0 and len(gene) == gene.count('A') + gene.count('T') + gene.count('G') + gene.count('C'):
                        genes.append(gene)
                    gene = ''
                else:
                    gene += line[:-1]
            if gene != '' and len(gene) % 3 == 0 and len(gene) == gene.count('A') + gene.count('T') + gene.count('G') + gene.count('C'):
                genes.append(gene)
    return genes


class NucleotideSubspace:
    def __init__(self, filename, nu):
        genes = read_file(filename)

        positions = []
        for sequence in genes:
            positions.append(coordinates(nucleotide_distribution(sequence)))

        clf = OneClassSVM(kernel='linear', nu=nu)
        clf.fit(positions)

        hyperplane = [list(clf.intercept_), list(clf.coef_[0])]
        self.hyperplane = hyperplane

        predictions = list(clf.predict(positions))
        self.probability = predictions.count(1) / len(predictions)
        self.predictions = predictions
        #self.training_data = genes

        self.center = array(coordinates({nucleotide: 1 for nucleotide in nucleotides}))
        self.distribution = nucleotide_distribution(''.join(genes))
        self.distances = [self.distance(gene) for gene in genes]
        self.cds = [self.center_distance(gene) for gene in genes]

    def distance(self, sequence):
        return hyperplane_distance(self.hyperplane, coordinates(nucleotide_distribution(sequence)))

    def center_distance(self, sequence):
        return linalg.norm(array(coordinates(nucleotide_distribution(sequence))) - self.center)

    def volume(self):
        oneplet_corners = []
        for i in range(len(nucleotides)):
            oneplet_corners.append([0 for _ in range(0, i)] + [1] + [0 for _ in range(i + 1, len(nucleotides))])

        distances = []
        for corner in oneplet_corners:
            distances.append(sign(hyperplane_distance(self.hyperplane, corner)))

        return distances.count(1) / len(nucleotides)


class CodonSubspace:
    def __init__(self, filename, nu):
        genes = read_file(filename)

        positions = []
        for sequence in genes:
            positions.append(coordinates(triplet_distribution(sequence)))

        clf = OneClassSVM(kernel='linear', nu=nu)
        clf.fit(positions)

        hyperplane = [list(clf.intercept_), list(clf.coef_[0])]
        self.hyperplane = hyperplane

        predictions = list(clf.predict(positions))
        self.probability = predictions.count(1) / len(predictions)
        self.predictions = predictions
        #self.training_data = genes

        self.center = array(coordinates({triplet: 1 for triplet in triplets}))
        self.distribution = triplet_distribution(''.join(genes))
        self.distances = [self.distance(gene) for gene in genes]
        self.cds = [self.center_distance(gene) for gene in genes]

    def distance(self, sequence):
        return hyperplane_distance(self.hyperplane, coordinates(triplet_distribution(sequence)))

    def center_distance(self, sequence):
        return linalg.norm(array(coordinates(triplet_distribution(sequence))) - self.center)

    def volume(self):
        triplet_corners = []
        for i in range(len(triplets)):
            triplet_corners.append([0 for _ in range(0, i)] + [1] + [0 for _ in range(i + 1, len(triplets))])

        distances = []
        for corner in triplet_corners:
            distances.append(sign(hyperplane_distance(self.hyperplane, corner)))

        return distances.count(1) / len(triplets)


class CodonPairSubspace:
    def __init__(self, filename, nu):
        genes = read_file(filename)

        positions = []
        for sequence in genes:
            positions.append(coordinates(sixplet_distribution(sequence)))

        clf = OneClassSVM(kernel='linear', nu=nu)
        clf.fit(positions)

        hyperplane = [list(clf.intercept_), list(clf.coef_[0])]
        self.hyperplane = hyperplane

        predictions = list(clf.predict(positions))
        self.probability = predictions.count(1) / len(predictions)
        self.predictions = predictions
        #self.training_data = genes

        self.center = array(coordinates({sixplet: 1 for sixplet in sixplets}))
        self.distribution = sixplet_distribution(''.join(genes))
        self.distances = [self.distance(gene) for gene in genes]
        self.cds = [self.center_distance(gene) for gene in genes]

    def distance(self, sequence):
        return hyperplane_distance(self.hyperplane, coordinates(sixplet_distribution(sequence)))

    def center_distance(self, sequence):
        return linalg.norm(array(coordinates(sixplet_distribution(sequence))) - self.center)

    def volume(self):
        sixplet_corners = []
        for i in range(len(sixplets)):
            sixplet_corners.append([0 for _ in range(0, i)] + [1] + [0 for _ in range(i + 1, len(sixplets))])

        distances = []
        for corner in sixplet_corners:
            distances.append(sign(hyperplane_distance(self.hyperplane, corner)))

        return distances.count(1) / len(sixplets)


codon_dictionary = [['TTT', 'TTC'],
                    ['TTA', 'TTG', 'CTT', 'CTC', 'CTA', 'CTG'],
                    ['ATT', 'ATC', 'ATA'],
                    ['ATG'],
                    ['GTT', 'GTC', 'GTA', 'GTG'],
                    ['TCT', 'TCC', 'TCA', 'TCG', 'AGT', 'AGC'],
                    ['CCT', 'CCC', 'CCA', 'CCG'],
                    ['ACT', 'ACC', 'ACA', 'ACG'],
                    ['GCT', 'GCC', 'GCA', 'GCG'],
                    ['TAT', 'TAC'],
                    ['CAT', 'CAC'],
                    ['CAA', 'CAG'],
                    ['AAT', 'AAC'],
                    ['AAA', 'AAG'],
                    ['GAT', 'GAC'],
                    ['GAA', 'GAG'],
                    ['TGT', 'TGC'],
                    ['TGG'],
                    ['CGT', 'CGC', 'CGA', 'CGG', 'AGA', 'AGG'],
                    ['GGT', 'GGC', 'GGA', 'GGG'],
                    ['TAA', 'TAG', 'TGA']]  # Stop

nucleotides = ['A', 'T', 'G', 'C']

triplets = []
for item in codon_dictionary:
    triplets.extend(item)

sixplets = []
for triplet1 in triplets:
    for triplet2 in triplets:
        sixplets.append(triplet1 + triplet2)
