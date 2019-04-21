#!usr/bin/env python

#from __future__ import print_function
import multiprocessing as mp
import os
import sys
from subprocess import getoutput


# print the manual
def manual_print():
    print('Usage:')
    print('  make database:')
    print('    python fast_search.py -p makedb -i db.fsa [-s 1110100010001011,11010110111] [-r AST,CFILMVY,DN,EQ,G,H,KR,P,W]')
    print('  search:')
    print('    python fast_search.py -p blastp -i qry.fsa -d db.fsa')
    print('Parameters:')
    print('  -p: program')
    print('  -i: query sequences in fasta format')
    print('  -l: start index of query sequences')
    print('  -u: end index of query sequences')
    print('  -L: start index of reference')
    print('  -U: end index of reference')
    print('  -d: ref database')
    print('  -D: index of ref, if this parameter is specified, only this part of formatted ref will be searched against')
    print('  -o: output file')
    print('  -O: write mode of output file. w: overwrite, a: append')
    print('  -s: spaced seed in format: 1111,1110,1001.. etc')
    print('  -r: reduced amino acid alphabet in format: AST,CFILMVY,DN,EQ,G,H,KR,P,W')
    print('  -v: number of hits to show')
    print('  -e: expect value')
    print('  -m: max ratio of pseudo hits that will trigger stop')
    print('  -j: distance between start sites of two neighbor seeds, greater will reduce the size of database')
    print('  -t: filter high frequency kmers whose counts > t')
    print('  -F: filter query sequence')
    print('  -M: bucket size of hash table, reduce this parameter will reduce memory usage but decrease sensitivity')
    print('  -c: chunck size of reference. default is 100K which means 100K sequences from reference will be used as database')
    print('  -a: number of processors to use')
    print('  -T: tmpdir to store tmp file. default ./tmpdir')


def main(cmd):
    os.system(cmd)

if __name__ == '__main__':

    argv = sys.argv
    here = os.path.dirname(os.path.abspath(__file__))

    fsearch = here+'/../lib/fsearch-c'
    #fsearch = here+'/../core/fsearch-c'

    # compile the core of search
    if not os.path.isfile(fsearch):
        from rpython.translator.goal import translate
        trans = os.path.dirname(translate.__file__) + '/translate.py'
        os.system('cd %s/../lib/ && %s %s fsearch.py'%(here, sys.executable, trans))
        #os.system('cd %s/../core/ && %s %s fsearch.py'%(here, sys.executable, trans))



    # 1x8 weight 8
    seeds = '11111111'
    #seeds = '1111111,11010010111,110100010001011'
    #seeds = '11111111,11101011011'
    # 8x6 weight 6
    #seeds = '1110010011,110010100011,10100100001011,10100010010101,11000001010011,1100010000001011,110100000001000011,1101000000000001000101'
    # 16x12 weight 12
    #seeds = '111101011101111,111011001100101111,1111001001010001001111,111100101000010010010111'
    aa_nr = 'AST,CFILMVY,DN,EQ,G,H,KR,P,W'
    #aa_nr = 'A,KR,EDNQ,C,G,H,ILVM,FYW,P,ST'
    #aa_nr = 'KREDQN,C,G,H,ILV,M,F,Y,W,P,STA'
    #aa_nr = 'G,P,IV,FYW,A,LM,EQRK,ND,HS,T,C'

    # recommand parameter:
    args = {'-p':'', '-v':'500', '-s':seeds, '-i':'', '-d':'', '-e':'1e-3', '-l':'-1', '-u':'-1', '-m':'1e-3', '-t':'-1', '-r':aa_nr, '-j':'1', '-F':'T', '-o':'', '-D':'', '-O':'wb', '-L':'-1', '-U':'-1', '-M':'120000000', '-c':'50000', '-a':'1', '-T': './tmpdir'}

    N = len(argv)
    for i in range(1, N):
        k = argv[i]
        if k in args:
            try:
                v = argv[i+1]
            except:
                break
            args[k] = v
        elif k[:2] in args and len(k) > 2:
            args[k[:2]] = k[2:]
        else:
            continue

    if args['-p'] not in ['makedb', 'blastp', 'bblastp', 'bblastp_noaln']:
        manual_print()
        raise SystemExit()
    elif args['-p'] == 'makedb' and args['-i'] == '':
        manual_print()
        raise SystemExit()
    elif args['-p'] == 'blastp':
        if args['-i'] == '' or args['-d'] == '':
            manual_print()
            raise SystemExit()
    else:
        manual_print()
        raise SystemExit()

    try:
        qry, ref, exp, bv, start, end, rstart, rend, miss, thr, step, flt, outfile, ref_idx, wrt, ht, chk, ssd, nr, ncpu, tmpdir = args['-i'], args['-d'], float(args['-e']), int(args['-v']), int(args['-l']), int(args['-u']), int(args['-L']), int(args['-U']), float(args['-m']), int(args['-t']), int(args['-j']), args['-F'], args['-o'], args['-D'], args['-O'], int(args['-M']), int(args['-c']), args['-s'], args['-r'], int(args['-a']), args['-T']
    except:
        manual_print()
        raise SystemExit()

    # get parameters and start the program
    if args['-p'] == 'makedb':
        os.system('%s -p makedb -i %s -s %s -r %s'%(fsearch, qry, ssd, nr))
    elif args['-p'] == 'blastp':
        # get the size of query sequence
        n = getoutput('grep -c \> %s'%qry).strip()
        N = int(n)
        cmds = []
        Start, End = list(map(int, [start, end]))
        if Start < 0:
            Start = 0
        if End < 0:
            End = N

        pool = mp.Pool(ncpu)
        Step = max(min(10000, abs(End-Start)//ncpu), 1)
        sts = []
        tmp_name = outfile.split(os.sep)[-1]
        # check the tmpdir
        os.system('mkdir -p %s'%tmpdir)

        #for st in xrange(0, N, 10000):
        for st in range(Start, End, Step):
            ed = min(N, st+Step)
            start, end = list(map(str, [st, ed]))
            #cmd = '%s -p blastp -i %s -d %s -e %s -v %s -l %s -u %s -L %s -U %s -m %s -t %s -j %s -F %s -D %s -O %s -M %s -c %s -s %s -r %s -o /tmp/%s.%012d'%(fsearch, qry, ref, exp, bv, start, end, rstart, rend, miss, thr, step, flt, ref_idx, wrt, ht, chk, ssd, nr, outfile, st)
            #cmd = '%s -p blastp -i %s -d %s -e %s -v %s -l %s -u %s -L %s -U %s -m %s -t %s -j %s -F %s -D %s -O %s -M %s -c %s -s %s -r %s -o /tmp/%s.%012d'%(fsearch, qry, ref, exp, bv, start, end, rstart, rend, miss, thr, step, flt, ref_idx, wrt, ht, chk, ssd, nr, tmp_name, st)
            #cmd = '%s -p blastp -i %s -d %s -e %s -v %s -l %s -u %s -L %s -U %s -m %s -t %s -j %s -F %s -D %s -O %s -M %s -c %s -s %s -r %s -o %s/%s.%012d'%(fsearch, qry, ref, exp, bv, start, end, rstart, rend, miss, thr, step, flt, ref_idx, wrt, ht, chk, ssd, nr, tmpdir, tmp_name, st)
            cmd = '%s -p blastp -i %s -d %s -e %s -v %s -l %s -u %s -L %s -U %s -m %s -t %s -j %s -F %s -D %s -O %s -M %s -c %s -s %s -r %s -o %s/%s.%012d -T %s'%(fsearch, qry, ref, exp, bv, start, end, rstart, rend, miss, thr, step, flt, ref_idx, wrt, ht, chk, ssd, nr, tmpdir, tmp_name, st, tmpdir)


            cmds.append(cmd)
            sts.append(st)
            #print cmd

        Ncmd = len(cmds)
        os.system('rm -f %s'%(outfile))
        for i in range(0, Ncmd, ncpu):
            pool.map(main, cmds[i:i+ncpu])
            for st in sts:
                #os.system('cat /tmp/%s.%012d >> %s'%(outfile, st, outfile))
                #os.system('cat /tmp/%s.%012d >> %s'%(tmp_name, st, outfile))
                os.system('cat %s/%s.%012d >> %s'%(tmpdir, tmp_name, st, outfile))

                #os.system('rm /tmp/%s.%012d'%(outfile, st))
                #os.system('rm /tmp/%s.%012d'%(tmp_name, st))
                os.system('rm %s/%s.%012d'%(tmpdir, tmp_name, st))


    else:
        manual_print()
        raise SystemExit()

#if not 'clean':
if 'clean':
    os.system('rm -rf %s'%tmpdir)
