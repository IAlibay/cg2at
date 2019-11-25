import os, sys
import numpy as np
from subprocess import Popen, PIPE
import subprocess, shlex
from time import gmtime, strftime
import math
import multiprocessing as mp
import argparse
import copy
from shutil import copyfile
from distutils.dir_util import copy_tree
import time
from string import ascii_uppercase
from pathlib import Path
import re
import datetime
import glob
from scipy.spatial import KDTree
import difflib
import gen, g_var, f_loc, at_mod


def build_atomistic_system(cg_residues, box_vec):
    system={}
    atomistic_fragments={}
#### for each residue type covert to atomistic except protein
    for residue_type in [key for value, key in enumerate(cg_residues) if key not in ['PROTEIN']]:
        if residue_type not in system and residue_type != 'ION':
            system[residue_type] = 0
    #### reset counters for each residue type
        print('Converting residue type: ' +residue_type)
    #### creates folder for residue type
        gen.mkdir_directory(g_var.working_dir+residue_type)
    #### fetches atoms for the residue type and centers then on cg bead

        atomistic_fragments[residue_type] = atomistic_non_protein(residue_type, cg_residues[residue_type])
        # print(atomistic_fragments[residue_type])
    #### if the residue type is in ['SOL', 'ION'] a single pdb is created
        if residue_type == 'SOL':            
            gen.mkdir_directory(g_var.working_dir+'SOL')  
        #### creates solvent directory and SOL key in system dictionay otherwise it appends solvent molecules to sol pdb
            if not os.path.exists(g_var.working_dir+'SOL'+'/SOL_0.pdb'):   
                # system['SOL']=0
                pdb_sol = open(g_var.working_dir+'SOL'+'/SOL_0.pdb', 'w')
                pdb_sol.write('REMARK    GENERATED BY sys_setup_script\nTITLE     SELF-ASSEMBLY-MAYBE\nREMARK    Good luck\n'
                              +box_vec+'MODEL        1\n')
            else:
                pdb_sol = open(g_var.working_dir+'SOL'+'/SOL_0.pdb', 'a')
        #### creates ion pdb with header
        if residue_type == 'ION':
            #### make minimisation directory and makes homogeneous directory structure
                gen.mkdir_directory(g_var.working_dir+'ION/min')
                pdb_ion = gen.create_pdb(g_var.working_dir+residue_type+'/'+residue_type+'_merged.pdb', box_vec)
    #### loop through all resids of that residue type 
        for resid in atomistic_fragments[residue_type]:
        #### if the residue type is not in ['SOL', 'ION'] a individual pdbs are created for each resid
            if residue_type not in ['SOL', 'ION']:
                pdb_output = gen.create_pdb(g_var.working_dir+residue_type+'/'+residue_type+'_'+str(resid)+'.pdb', box_vec)         
                atomistic_fragments[residue_type][resid] = check_hydrogens(atomistic_fragments[residue_type][resid])
            ####### check if any atoms in residue overlap #######
                coord=[]
                for atom in atomistic_fragments[residue_type][resid]:
                    coord.append(atomistic_fragments[residue_type][resid][atom]['coord'])
                coord=at_mod.check_atom_overlap(coord)
                for atom_val, atom in enumerate(atomistic_fragments[residue_type][resid]):
                    atomistic_fragments[residue_type][resid][atom]['coord']=coord[atom_val]

            for at_id, atom in enumerate(atomistic_fragments[residue_type][resid]):
            #### separates out the water molecules from the ion in the fragment
                if residue_type in ['SOL']:
                    if atomistic_fragments[residue_type][resid][at_id+1]['frag_mass'] > 1:                  
                        system['SOL']+=1
                    short_line=atomistic_fragments[residue_type][resid][at_id+1]
                    pdb_sol.write(g_var.pdbline%((at_id+1,short_line['atom'],short_line['res_type'],' ',1,short_line['coord'][0],
                                  short_line['coord'][1],short_line['coord'][2],short_line['extra'],short_line['connect']))+'\n')
                elif residue_type in ['ION']:
                #### write ion coordinate out
                    short_line=atomistic_fragments[residue_type][resid][at_id+1]
                    pdb_ion.write(g_var.pdbline%((at_id+1,short_line['atom'],short_line['res_type'],' ',1,short_line['coord'][0],
                                  short_line['coord'][1],short_line['coord'][2],short_line['extra'],short_line['connect']))+'\n')
                    if atomistic_fragments[residue_type][resid][at_id+1]['res_type'] != 'SOL':
                        if atomistic_fragments[residue_type][resid][at_id+1]['res_type'] not in system:
                            system[atomistic_fragments[residue_type][resid][at_id+1]['res_type']]=1
                        else:
                            system[atomistic_fragments[residue_type][resid][at_id+1]['res_type']]+=1
                else:
                #### write residue out to a pdb file
                    short_line=atomistic_fragments[residue_type][resid][at_id+1]
                    pdb_output.write(g_var.pdbline%((at_id+1,short_line['atom'],short_line['res_type'],' ',1,short_line['coord'][0],
                                     short_line['coord'][1],short_line['coord'][2],short_line['extra'],short_line['connect']))+'\n')
        if residue_type not in ['SOL','ION']:
        #### adds retype to system dictionary
            system[residue_type]=int(resid)+1
    return system 

def atomistic_non_protein(cg_residue_type,cg_residues):
    atomistic_fragments={}  #### residue dictionary
#### run through every residue in a particular residue type
    for cg_resid, cg_residue in enumerate(cg_residues):
    #### get atomistic fragments for each bead and connectivity with other beads
        at_residues, connect = at_mod.get_atomistic_fragments(cg_residue_type,cg_residues[cg_residue], cg_resid)   
        atomistic_fragments[cg_resid]={}  #### creats key in atomistic_fragments for each residue eg atomistic_fragments[1]
    #### runs through all beads in each resid
        for bead_number, cg_bead in enumerate(cg_residues[cg_residue]):
        #### if cg_residue_type not in ['SOL', 'ION'] as they have no connectivity 
            if cg_residue_type not in ['SOL', 'ION']:
            #### finds all beads that the cg_bead is connected to, and returns atom coord, cg coord and center of cg_bead
                at_connections,cg_connections, center=at_mod.connectivity(bead_number, cg_bead, connect, at_residues, cg_residues,cg_residue)
            #### rotates at_connections to finds minimum RMS distance with cg_connections 
                if len(at_connections)==len(cg_connections):
                    try:
                        xyz_rot_apply=at_mod.rotate(np.array(at_connections), np.array(cg_connections), False)
                    except:
                        sys.exit(str(cg_bead)+' '+str(at_connections)+' '+str(cg_connections))
                else:
                    sys.exit('the bead '+cg_bead+' in residue '+cg_residues[cg_residue][cg_bead]['residue_name']+' contains the wrong number of connections')
        #### if ION/SOL a random rotation is applied to the cluster 
            else:
                center=cg_residues[cg_residue][cg_bead]['coord']
                xyz_rot_apply=[np.random.uniform(0, math.pi*2), np.random.uniform(0, math.pi*2), np.random.uniform(0, math.pi*2)]
            #### applies optimum rotation to each atom in the fragment 
            for atom in at_residues[cg_bead]:
                at_residues[cg_bead][atom]['coord']=at_mod.rotate_atom(at_residues[cg_bead][atom]['coord'], center, xyz_rot_apply)  ### applies rotation
            #### adds bead number to at_residues dictionary
                at_residues[cg_bead][atom].update({'cg_bead':bead_number+1})
            #### adds atomistic fragment to new dictionary atomistic_fragments[resid][atom number] allows reordering of atoms by atom number in fragment database
                atomistic_fragments[cg_resid][int(atom)]=at_residues[cg_bead][atom]
    return atomistic_fragments


def check_hydrogens(residue):
#### finds the connecting carbons and their associated carbons [carbon atom, hydrogen ref number, connecting ref number]    
    connect=[]
    for atom_num, atom in enumerate(residue):
        if residue[atom]['connect'] > 0 and residue[atom]['extra'] > 1:
            connect.append([atom, residue[atom]['extra'],  residue[atom]['connect']]) 
    connect=np.array(connect)
    for atom_num, carbon in enumerate(connect):
        h_coord=[]
        h_atoms=[]
    #### strips coordinates 
        for atom_num, atom in enumerate(residue):
            if residue[atom]['extra'] == carbon[1] and atom != carbon[0]:
                h_coord.append(residue[atom]['coord'])
                h_atoms.append(atom)
            if residue[atom]['connect'] == carbon[2] and atom != carbon[0]:
                connecting_coord=residue[atom]['coord']
        h_coord=np.array(h_coord)
    #### gets COM of Hydrogens
        h_com=np.array([np.mean(h_coord[:,0]),np.mean(h_coord[:,1]),np.mean(h_coord[:,2])]) ### center of mass of hydrogens
    #### vector between H COM and bonded carbon 
        vector=np.array([h_com[0]-residue[carbon[0]]['coord'][0],h_com[1]-residue[carbon[0]]['coord'][1],h_com[2]-residue[carbon[0]]['coord'][2]])
    #### flips  
        h_com_f=h_com+vector*2
        d1 = np.sqrt((h_com[0]-connecting_coord[0])**2+(h_com[1]-connecting_coord[1])**2+(h_com[2]-connecting_coord[2])**2)
        d2 = np.sqrt((h_com_f[0]-connecting_coord[0])**2+(h_com_f[1]-connecting_coord[1])**2+(h_com_f[2]-connecting_coord[2])**2)
        if d2<d1 and len(h_coord) == 2:
            for h_at in h_atoms:
                residue[h_at]['coord']=residue[h_at]['coord']+vector*2
        elif d2>d1 and len(h_coord) == 1: 
            for h_at in h_atoms:
                residue[h_at]['coord']=residue[h_at]['coord']-vector*2

    return residue
