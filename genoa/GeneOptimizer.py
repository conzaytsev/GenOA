from random import randint, choices


def crossingover(sequence1, sequence2):
    point1 = randint(0, len(sequence1))
    point2 = randint(0, len(sequence1))
    while point2 == point1:
        point2 = randint(0, len(sequence1))
    if point1 > point2:
        point1, point2 = point2, point1
    new_sequence1 = sequence1[: point1] + sequence2[point1: point2] + sequence1[point2:]
    new_sequence2 = sequence2[: point1] + sequence1[point1: point2] + sequence2[point2:]
    return new_sequence1, new_sequence2


def randomize(encoded, codon_dictionary):
    randomized = ''
    for i in encoded:
        randomized += codon_dictionary[i][randint(0, len(codon_dictionary[i]) - 1)]
    return randomized


def nonrandomize(encoded, triplet_encoded, sixplet_dictionary, sixplet_frequencies, codon_dictionary, codon_context):
    randomized = choices(sixplet_dictionary[encoded[0]], sixplet_frequencies[encoded[0]])[0]
    for i in triplet_encoded[2:]:
        randomized += choices(codon_dictionary[i], codon_context[randomized[-3:]][i])[0]
    return randomized


def translate(aa_sequence):
    dictionary = {'F': 'TTT', 'L': 'TTA', 'I': 'ATT', 'M': 'ATG', 'V': 'GTT', 'S': 'TCT', 'P': 'CCT', 'T': 'ACT',
                  'A': 'GCT', 'Y': 'TAT', 'H': 'CAT', 'Q': 'CAA', 'N': 'AAT', 'K': 'AAA', 'D': 'GAT', 'E': 'GAA',
                  'C': 'TGT', 'W': 'TGG', 'R': 'CGT', 'G': 'GGT'}
    nuc_sequence = ''
    for letter in aa_sequence:
        nuc_sequence += dictionary[letter]
    return nuc_sequence


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
                    if gene != '' and len(gene) % 3 == 0 and len(gene) == gene.count('A') + gene.count(
                            'T') + gene.count('G') + gene.count('C'):
                        genes.append(gene)
                    gene = ''
                else:
                    gene += line[:-1]
            if gene != '' and len(gene) % 3 == 0 and len(gene) == gene.count('A') + gene.count('T') + gene.count(
                    'G') + gene.count('C'):
                genes.append(gene)
    return genes


def gc_content(sequence):
    return (sequence.count('G') + sequence.count('C')) / len(sequence)


def restriction_check(sequence, restriction_sites):
    for site in restriction_sites:
        if sequence.find(site) > -1:
            return False
    return True


class Optimizer:
    def __init__(self, expression_model, subspace_model, input_sequence, set_size, expression_priority,
                 subspace_priority, center_priority, gc_priority, n_children, max_iterations, restriction_sites):
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

        reverse_dictionary = {}
        for i in range(len(codon_dictionary)):
            for j in codon_dictionary[i]:
                reverse_dictionary[j] = i

        triplets = []
        for item in codon_dictionary:
            triplets.extend(item)

        triplet_encoded = []
        for i in range(0, len(input_sequence), 3):
            triplet_encoded.append(reverse_dictionary[input_sequence[i:i + 3]])

        sequence_set = []
        if subspace_priority == center_priority == 0:
            while len(sequence_set) < set_size:
                sequence_set.append(randomize(triplet_encoded, codon_dictionary))
        else:
            sixplet_dictionary = []
            for first in codon_dictionary:
                for second in codon_dictionary:
                    sixplet_dictionary.append([])
                    for first_codon in first:
                        for second_codon in second:
                            sixplet_dictionary[-1].append(first_codon + second_codon)

            sixplet_reverse_dictionary = {}
            for i in range(len(sixplet_dictionary)):
                for j in sixplet_dictionary[i]:
                    sixplet_reverse_dictionary[j] = i

            sixplets = []
            for i in triplets:
                for j in triplets:
                    sixplets.append(i + j)

            distribution = subspace_model.distribution

            sixplet_frequencies = []
            for item in sixplet_dictionary:
                sixplet_frequencies.append([])
                for sixplet in item:
                    sixplet_frequencies[-1].append(distribution[sixplet])

            codon_context = {}
            for first_triplet in triplets:
                codon_context[first_triplet] = []
                for item in codon_dictionary:
                    codon_context[first_triplet].append(
                        [distribution[first_triplet + second_triplet] for second_triplet in item])

            encoded = []
            for i in range(0, len(input_sequence) - 3, 3):
                encoded.append(sixplet_reverse_dictionary[input_sequence[i:i + 6]])

            while len(sequence_set) < set_size:
                sequence = nonrandomize(encoded, triplet_encoded, sixplet_dictionary, sixplet_frequencies,
                                        codon_dictionary, codon_context)
                if restriction_check(sequence, restriction_sites):
                    sequence_set.append(sequence)

        self.expression_model = expression_model
        self.subspace_model = subspace_model
        self.sequence_set = sequence_set
        self.expression_priority = expression_priority
        self.subspace_priority = subspace_priority
        self.center_priority = center_priority
        self.gc_priority = gc_priority
        self.max_iterations = max_iterations
        self.n_children = n_children
        self.restriction_sites = restriction_sites
        self.expression_weight = 0
        self.subspace_weight = 0
        self.center_weight = 0
        self.gc_weight = 0

    def score(self, sequence, target_score, target_distance, target_center, target_gc):
        value = 0
        if self.expression_priority > 0:
            value += abs(self.expression_model.predict(sequence) - target_score) * self.expression_weight
        if self.subspace_priority > 0:
            value += abs(self.subspace_model.distance(sequence) - target_distance) * self.subspace_weight
        if self.center_priority > 0:
            value += abs(self.subspace_model.center_distance(sequence) - target_center) * self.center_weight
        if self.gc_priority > 0:
            value += abs(gc_content(sequence) - target_gc) * self.gc_weight
        return 1 / value

    def optimize(self, target_score, target_distance, target_center, target_gc):
        self.expression_weight = 0.1 * self.expression_priority

        distance_variation = sorted(self.subspace_model.distances)
        self.subspace_weight = 1 / abs(distance_variation[int(len(distance_variation) * 0.001)] - distance_variation[
            int(len(distance_variation) * 0.999)]) * self.subspace_priority

        self.center_weight = 1 * self.center_priority

        self.gc_weight = 1 * self.gc_priority

        score_set = []
        for sequence in self.sequence_set:
            score_set.append(self.score(sequence, target_score, target_distance, target_center, target_gc))

        sequence_set = [x for y, x in sorted(zip(score_set, self.sequence_set))]
        score_set.sort()

        counter = 0
        best_score = 0
        while counter < self.max_iterations:
            counter += 1
            children = []
            while len(children) < self.n_children:
                parent1 = choices(sequence_set, score_set)[0]
                parent2 = choices(sequence_set, score_set)[0]
                while parent2 == parent1:
                    parent2 = choices(sequence_set, score_set)[0]
                child1, child2 = crossingover(parent1, parent2)
                if child1 != parent1 and child1 != parent2:
                    if restriction_check(child1, self.restriction_sites):
                        children.append(child1)
                    if restriction_check(child2, self.restriction_sites):
                        children.append(child2)

            children_score = []
            for sequence in children:
                children_score.append(self.score(sequence, target_score, target_distance, target_center, target_gc))

            sequence_set.extend(children)
            score_set.extend(children_score)
            sequence_set = [x for y, x in sorted(zip(score_set, sequence_set))]
            score_set.sort()

            for i in range(len(children)):
                sequence_set.pop(0)
                score_set.pop(0)

            if score_set[-1] > best_score:
                best_score = score_set[-1]
                counter = 0

        return sequence_set[-1]
