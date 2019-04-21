#!usr/bin/env python
import sys
from Bio import SeqIO
import networkx as nx
from collections import Counter
import os
#from subprocess import getoutput
if sys.version_info.major == 2:
    from commands import getoutput
else:
    from subprocess import getoutput


# do the core gene find
def manual_print():
    print('This script used reciprocal best hits to identify orthologs between species and a given species, then extract sequences of these orthologs and do a msa, finally, concatenate all the msa.')
    print('Usage:')
    print('  python this.py -i foo.m8 -f foo.fsa [-r taxon]\n')
    print('Parameters:')
    print(' -i: blast -m8 or fastclust sc format:\n     xxxx|yyyy\tXXXX|YYYY\t...: xxxx/XXXX is taxon name and yyyy/YYYY is unique identifier in that taxon')
    print(' -f: protein/gene fasta file. The header should be like xxxx|yyyy: xxxx is taxon name and yyyy is unqiue identifier in that taxon')
    print(' -r: taxonomy name used as reference [optional]')


argv = sys.argv
# recommand parameter:
args = {'-i': '', '-f': '', '-r': ''}

N = len(argv)
for i in range(1, N):
    k = argv[i]
    if k in args:
        try:
            v = argv[i + 1]
        except:
            break
        args[k] = v
    elif k[:2] in args and len(k) > 2:
        args[k[:2]] = k[2:]
    else:
        continue

if args['-i'] == '' or args['-f'] == '':
    manual_print()
    raise SystemExit()

try:
    orth, fas, taxon = args['-i'], args['-f'], args['-r']
except:
    manual_print()
    raise SystemExit()

# check reference taxon
taxon_ct = Counter()
f = open(fas, 'r')
for i in f:
    if i.startswith('>'):
        j = i[1:-1].split('|')[0]
        taxon_ct[j] += 1

f.close()

# if taxon not specified, then choose the taxon with most genes
taxon_hf = list(taxon_ct.items())
taxon_hf.sort(key=lambda x: x[1], reverse=True)
taxon_N = len(taxon_hf)
taxon_max = taxon_hf[0]
taxon = taxon == '' and taxon_max[0] or taxon

#taxon_idx = {b: a for a, b in enumerate(taxon_ct.keys())}
taxon_idx = {b: a for a, b in enumerate([elem[0] for elem in taxon_hf])}


# get the ortholog
# find ortholog in all tax


def m8parse(f):
    flag = None
    out = []
    for i in f:
        j = i[:-1].split('\t')
        qid = j[0]
        if flag != qid:
            if out:
                out.sort(key=lambda x: -float(x[11]))
                yield out
            flag = qid
            out = [j]
        else:
            out.append(j)

    if out:
        out.sort(key=lambda x: -float(x[11]))
        yield out

Orth = orth
#os.system('mkdir -p ./alns_tmp/')
os.system('mkdir -p %s_alns_tmp/' % Orth)

f = open(orth, 'r')
ortholog = {}
for i in m8parse(f):
    Os = {}
    for j in i:
        qid, sid = j[:2]
        qtx, stx = qid.split('|')[0], sid.split('|')[0]
        key = (qtx, stx)
        if qtx == taxon and stx != taxon:
            if key not in Os:
                Os[key] = [qid, sid]
        else:
            continue

    for qid, sid in Os.values():
        qtx, stx = qid.split('|')[0], sid.split('|')[0]
        if qid not in ortholog:
            ortholog[qid] = [-1] * taxon_N * 2
            ortholog[qid][:2] = qid, 1

        sidx = taxon_idx[stx] * 2
        ortholog[qid][sidx] = sid
        #ortholog[qid][sidx + 1] = 1
        # print 'ortho', ortholog[qid]

f.close()

f = open(orth, 'r')
for i in m8parse(f):
    Os = {}
    for j in i:
        qid, sid = j[:2]
        qtx, stx = qid.split('|')[0], sid.split('|')[0]
        key = (qtx, stx)
        if qtx != taxon and stx == taxon:
            if key not in Os:
                Os[key] = [sid, qid]
        else:
            continue

    # if Os:
    #   print 'yes', Os.values(), len(ortholog)

    for qid, sid in Os.values():
        if qid not in ortholog:
            # print 'no found', qid
            continue

        qtx, stx = qid.split('|')[0], sid.split('|')[0]
        sidx = taxon_idx[stx] * 2
        if ortholog[qid][sidx] == sid:
            ortholog[qid][sidx + 1] = 1
            # print 'yes match', ortholog[qid][sidx], sid

        # else:
        #   print 'not match', ortholog[qid][sidx], sid

        # print 'ortho', ortholog[qid]


f.close()


# print 'taxon N is', taxon_N

# print ortholog
orths = []
orths_set = set()
# for i in ortholog.keys():
for j in list(ortholog.values()):
    # j = ortholog[i]
    orth = [a for a, b in zip(j[::2], j[1::2]) if b == 1]
    # print orth, taxon, j
    rate = len(orth) * 1. / taxon_N
    if rate >= .9:
        orths.append(orth)
        orths_set.update(orth)
    else:
        continue
        # print rate, len(orth), taxon_N

seqs_dict = {}
for i in SeqIO.parse(fas, 'fasta'):
    if i.id in orths_set:
        seqs_dict[i.id] = i

# print len(seqs)
# raise SystemExit()

# write the seq to file
orths_N = len(orths)
for i in range(orths_N):
    j = orths[i]
    seqs = [seqs_dict[elem] for elem in j]
    #_o = open('./alns_tmp/%d.fsa' % i, 'w')
    _o = open('%s_alns_tmp/%d.fsa' % (Orth, i), 'w')
    #_o.write('>%s|%s\n%s\n' % (tax, qid, sq))
    SeqIO.write(seqs, _o, 'fasta')
    _o.close()

# raise SystemExit()
# use the muscle to aln
if not getoutput('type famsa').endswith('not found'):
    #cmd = 'famsa -t 0 %s_alns_tmp/%d.fsa %s_alns_tmp/%d.fsa.aln' % (Orth, i, Orth, i)
    cmd = 'famsa -t 4 %s_alns_tmp/%d.fsa %s_alns_tmp/%d.fsa.aln'
elif not getoutput('type mafft').endswith('not found'):
    #cmd = 'mafft --quiet --auto %s_alns_tmp/%d.fsa > %s_alns_tmp/%d.fsa.aln' % (Orth, i, Orth, i)
    cmd = 'mafft --quiet --auto %s_alns_tmp/%d.fsa > %s_alns_tmp/%d.fsa.aln'
elif not getoutput('type muscle').endswith('not found'):
    #cmd = 'muscle -in %s_alns_tmp/%d.fsa -out %s_alns_tmp/%d.fsa.aln -fasta -quiet' % (Orth, i, Orth, i)
    cmd = 'muscle -in %s_alns_tmp/%d.fsa -out %s_alns_tmp/%d.fsa.aln -fasta -quiet'
else:
    print('only support famsa|mafft|muscle')
    raise SystemExit()


for i in range(orths_N):
    # break
    #os.system('muscle -in %s_alns_tmp/%d.fsa -out %s_alns_tmp/%d.fsa.aln -fasta -quiet' % (Orth, i, Orth, i))
    os.system(cmd % (Orth, i, Orth, i))
    # os.system('/home/zhans/tools/tree_tools/trimal/source/trimal -in ./alns_tmp/%d.fsa.aln -out ./alns_tmp/%d.fsa.aln.trim -automated1' % (i, i))


# N = len([elem for elem in os.listdir('./tmpdir') if elem.endswith('.trim')])
# print 'total N', N

taxon_set = set(taxon_ct.keys())
tree = {}
for i in range(orths_N):
    # seqs = SeqIO.parse('./alns_tmp/%d.fsa.aln.trim' % i, 'fasta')
    #seqs = SeqIO.parse('./alns_tmp/%d.fsa.aln' % i, 'fasta')
    seqs = SeqIO.parse('%s_alns_tmp/%d.fsa.aln' % (Orth, i), 'fasta')
    visit = set()
    for j in seqs:
        taxon = j.id.split('|', 2)[0]
        try:
            tree[taxon].append(str(j.seq))
        except:
            tree[taxon] = [str(j.seq)]
        empty = '-' * len(j.seq)
        visit.add(taxon)

    for taxon in (taxon_set - visit):
        try:
            tree[taxon].append(empty)
        except:
            tree[taxon] = [empty]


# print 'tree is', tree

# flag = 0
N = len(tree)
L = len(''.join(list(tree.values())[0]))
# print ' %d %d' % (N, L)
for i in tree:
    hd = '>' + i
    # hd = i
    sq = ''.join(tree[i])
    # print hd, sq
    print(hd)
    print(sq)


#os.system('rm -rf %s_alns_tmp'%Orth)
