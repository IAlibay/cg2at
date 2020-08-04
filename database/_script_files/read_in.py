#!/usr/bin/env python3

import sys, os
import numpy as np
import math
import copy
import gen, g_var, f_loc

def read_initial_cg_pdb():
    
    print('\nThis script is now hopefully doing the following (Good luck):\n\nReading in your CG representation\n')
    # cg_residues={}  
    residue_list={} ## a dictionary of bead in each residue eg residue_list[bead name(BB)][residue_name(PO4)/coordinates(coord)]
    count=0  ### residue counter initialisation
    with open(g_var.input_directory+'CG_INPUT.pdb', 'r') as pdb_input:
        for line in pdb_input.readlines():
            if line.startswith('ATOM'):
                line_sep = gen.pdbatom(line)
                line_sep['atom_name'], line_sep['residue_name'] = swap(line_sep['atom_name'], line_sep['residue_name'], line_sep['residue_id']) ## implements swap group
                # print(1, line_sep['atom_name'], line_sep['residue_name'], line_sep['residue_id'])
                if 'SKIP' not in [line_sep['atom_name'].upper(), line_sep['residue_name'].upper()]:
                    # print(2, line_sep['atom_name'], line_sep['residue_name'], line_sep['residue_id'])
#### set up resnames in dictionaries
                    add_residue_to_dictionary(line_sep)
    #### sets up previous resid id 
                    if 'residue_prev' not in locals(): 
                        residue_prev=line_sep.copy() 
    #### if resid the same as previous line
                    if residue_prev['residue_id'] == line_sep['residue_id'] and line_sep['residue_name'] == residue_prev['residue_name']:   ### if resid is the same as the previous line, it adds resname and coordinates to the atom name key in residue_list 
                        residue_list[line_sep['atom_name']]={'residue_name':line_sep['residue_name'],'coord':np.array([line_sep['x'],line_sep['y'],line_sep['z']])}
                        line_sep_prev=line_sep.copy()
    #### if resids are different then the residue list is added to cg_residues
                    else: 
                        if line_sep_prev['residue_name'] not in f_loc.p_residues:
                            g_var.cg_residues[line_sep_prev['residue_name']][count]={} ### then create sub dictionary cg_residues[resname][count]
                            g_var.cg_residues[line_sep_prev['residue_name']][count]=residue_list ### adds residue list to dictionary key cg_residues[resname][count]
                            if line_sep_prev['residue_name'] == 'ION':
                                g_var.cg_residues['SOL'][count]={}
                                sol_res_list={}

                                sol_res_list[f_loc.water]=residue_list[line_sep_prev['atom_name']].copy()
                                sol_res_list[f_loc.water]['residue_name']='SOL'
                                g_var.cg_residues['SOL'][count]=sol_res_list
                        else:
                            g_var.cg_residues['PROTEIN'][count]={} ### then create sub dictionary cg_residues['PROTEIN'][count]
                            g_var.cg_residues['PROTEIN'][count]=residue_list ### adds residue list to dictionary key cg_residues['PROTEIN'][count]
    #### updates dictionaries and counters
                        residue_list={}  ### resets residue list
                        count+=1 ### moves counter along to next residue
                        residue_list[line_sep['atom_name']]={'residue_name':line_sep['residue_name'],'coord':np.array([line_sep['x'],line_sep['y'],line_sep['z']])} ### it adds resname and coordinates to the atom name key in residue_list
                        residue_prev=line_sep.copy()    ### updates residue_prev with new resid
                        line_sep_prev=line_sep.copy()
#### finds box vectors
            if line.startswith('CRYST'): ### collects box vectors from pdb
                box_vec=line
#### adds final residue to cg_residues in the same manner as above
    if 'line_sep' not in locals():
        sys.exit('input coarsegrain structure seems to contain no beads')
    if 'SKIP' == line_sep['residue_name']:
        line_sep['residue_name']=line_sep_prev['residue_name']
        line_sep['atom_name']=line_sep_prev['atom_name']
    if line_sep['residue_name'] in f_loc.p_residues: 
        if count not in g_var.cg_residues['PROTEIN']:
            g_var.cg_residues['PROTEIN'][count]={}
        g_var.cg_residues['PROTEIN'][count]=residue_list
    else:
        if count not in g_var.cg_residues[line_sep['residue_name']]:
            g_var.cg_residues[line_sep['residue_name']][count]={}
        g_var.cg_residues[line_sep['residue_name']][count]=residue_list
        if line_sep['residue_name'] == 'ION':
            g_var.cg_residues['SOL'][count]={}
            sol_res_list={}
            sol_res_list[f_loc.water]=residue_list[line_sep['atom_name']].copy()
            sol_res_list[f_loc.water]['residue_name']='SOL'
            g_var.cg_residues['SOL'][count]=sol_res_list
#### checks if box vectors exist
    if 'box_vec' not in locals():### stops script if it cannot find box vectors
        sys.exit('missing box vectors')
    for key in g_var.cg_residues:
        if len(g_var.cg_residues[key]) == 0:
            sys.exit('there is a issue with the residue type: '+key)
    return box_vec

def add_residue_to_dictionary(line_sep):
    if line_sep['residue_name'] in f_loc.p_residues: ## if in protein database 
        if 'PROTEIN' not in g_var.cg_residues:  ## if protein does not exist add to dict
            g_var.cg_residues['PROTEIN']={}
    elif line_sep['residue_name'] in g_var.cg_water_types: 
        line_sep['residue_name']='SOL'
        if line_sep['residue_name'] not in g_var.cg_residues: ## if residue type does not exist add to dict
            g_var.cg_residues[line_sep['residue_name']]={}
        line_sep['atom_name']=f_loc.water
    elif line_sep['residue_name'] in f_loc.np_residues:
        if line_sep['residue_name'] not in g_var.cg_residues:
            g_var.cg_residues[line_sep['residue_name']]={}
        if line_sep['residue_name'] == 'ION' and 'SOL' not in g_var.cg_residues:
            g_var.cg_residues['SOL']={}
    elif line_sep['residue_name'] == 'SKIP':
        pass
    else:
        sys.exit('\n'+line_sep['residue_name']+' is not in the fragment database!') 


def check_new_box(coord,box, new_box):
    for xyz_val, xyz in enumerate(new_box):
        if g_var.box[xyz_val] != 0:
            lower, upper = (float(box[xyz_val])/2)-(float(xyz)/2), (float(box[xyz_val])/2)+(float(xyz)/2)
            if  lower >= coord[xyz_val] or coord[xyz_val] >= upper: 
                return True
    return False

def real_box_vectors(box_vec):
    x, y, z, yz, xz, xy = [float(i) for i in box_vec.split()[1:7]]
    # return real-space vector
    cyz, cxz, cxy, sxy = math.cos(np.radians(yz)), math.cos(np.radians(xz)), math.cos(np.radians(xy)) , math.sin(np.radians(xy))
    wx, wy             = z*cxz, z*(cyz-cxz*cxy)/sxy
    wz                 = math.sqrt(z**2 - wx**2 - wy**2)
    r_b_vec = np.array([[x, 0, 0], [y*cxy, y*sxy, 0], [wx, wy, wz]]).T
    r_b_inv = np.linalg.inv(r_b_vec).T
    return r_b_vec, r_b_inv

def brute_mic(p1, p2, r_b_vec):
    result = None
    n = 2
    if gen.calculate_distance(p1, p2) > 10:
        for x in range(-n, n+1):
            for y in range(-n, n+1):
                for z in range(-n, n+1):
                    rp = p2+np.dot(r_b_vec, [x,y,z])
                    d = gen.calculate_distance(p1, rp)
                    if (result is None) or (result[1] > d):
                        result = (rp, d)
        if result[1] < 10:
            return result[0]
        else:
            return p2
    else:
        return p2

def fix_pbc(box_vec, new_box, box_shift):
#### fixes box PBC
    r_b_vec, r_b_inv = real_box_vectors(box_vec)
    new_box = new_box.split()[1:4]
    for residue_type in g_var.cg_residues:
        cut_keys=[]
        for res_val, residue in enumerate(g_var.cg_residues[residue_type]):
            for bead_val, bead in enumerate(g_var.cg_residues[residue_type][residue]):
                if g_var.box != None and residue_type not in ['PROTEIN']:
                    cut = check_new_box(g_var.cg_residues[residue_type][residue][bead]['coord'],box_vec.split()[1:4], new_box)
                    if cut:
                        cut_keys.append(residue)
                        break
                if residue_type in ['PROTEIN'] and bead == f_loc.res_top[g_var.cg_residues[residue_type][residue][bead]['residue_name']]['BACKBONE']:
                    BB_bead = f_loc.res_top[g_var.cg_residues[residue_type][residue][bead]['residue_name']]['BACKBONE']
                    if res_val != 0 :
                        BB_cur = g_var.cg_residues[residue_type][residue][BB_bead]['coord']
                        g_var.cg_residues[residue_type][residue][BB_bead]['coord'] = brute_mic(BB_pre, BB_cur, r_b_vec)
                    BB_pre = g_var.cg_residues[residue_type][residue][BB_bead]['coord'].copy()
                if bead_val != 0 and residue_type not in ['ION','SOL']:
                    g_var.cg_residues[residue_type][residue][bead]['coord'] = brute_mic(g_var.cg_residues[residue_type][residue][bead_prev]['coord'],
                                                                                    g_var.cg_residues[residue_type][residue][bead]['coord'], r_b_vec)
                bead_prev=bead
                if g_var.box != None:
                    g_var.cg_residues[residue_type][residue][bead]['coord'] = g_var.cg_residues[residue_type][residue][bead]['coord']-box_shift
        for key in cut_keys:
            g_var.cg_residues[residue_type].pop(key)

def swap(atom, residue, resid):
    if atom in f_loc.ions and residue != 'ION':
        residue = 'ION'
    if residue in f_loc.swap_dict:
        for key, value in f_loc.swap_dict[residue].items():
            break
        if 'ALL' in f_loc.swap_dict[residue][key]['resid'] or resid in f_loc.swap_dict[residue][key]['resid']:
            if atom in f_loc.swap_dict[residue][key]:
                atom = f_loc.swap_dict[residue][key][atom]
            residue = key.split(':')[1].upper()
    elif residue == 'ION' and atom in f_loc.swap_dict:
        for key, value in f_loc.swap_dict[atom].items():
            break
        if 'ALL' in f_loc.swap_dict[atom][key]['resid'] or resid in f_loc.swap_dict[atom][key]['resid']:
            if atom in f_loc.swap_dict[atom][key]:
                atom = f_loc.swap_dict[atom][key][atom]
            residue = key.split(':')[1].upper()
    return atom, residue


##################################################################  User supplied protein ##############

def read_in_atomistic(protein):
#### reset location and check if pdb exists  
    os.chdir(g_var.start_dir)
    if not os.path.exists(protein):
        sys.exit('cannot find atomistic protein : '+protein)
#### read in atomistic fragments into dictionary residue_list[0]=x,y,z,atom_name    
    atomistic_protein_input={}
    if g_var.input_directory in protein:
        chain_count=g_var.chain_count
    else:
        chain_count = 0
#### read in pdb
    ter_residues=[]
    r_b_vec, r_b_inv = real_box_vectors(g_var.box_vec)
    with open(protein, 'r') as pdb_input:
        atomistic_protein_input[chain_count]={}
        for line_nr, line in enumerate(pdb_input.readlines()):
            #### separate line 
            run=False ## turns to true is line is a bead/atom
            if line.startswith('ATOM'):
                line_sep = gen.pdbatom(line)
                # print(line_sep['atom_name'])
                if not gen.is_hydrogen(line_sep['atom_name']):
                    run=True
                if line_sep['residue_name'] in f_loc.mod_residues:
                    run=True
            #### if line is correct
            if run:
                if line_sep['residue_name'] in f_loc.p_residues:
                    # print(f_loc.p_residues)
                    if not gen.is_hydrogen(line_sep['atom_name']) or line_sep['residue_name'] in f_loc.mod_residues:  
                    #### sorts out wrong atoms in terminal residues
                        if line_sep['atom_name'] in ['OT', 'O1', 'O2']:
                            line_sep['atom_name']='O'
                    #### makes C_terminal connecting atom variable  
                        if 'prev_atom_coord' in locals():
                            line_sep['x'],line_sep['y'],line_sep['z'] = brute_mic(prev_atom_coord, [line_sep['x'],line_sep['y'],line_sep['z']], r_b_vec)
                        if line_sep['atom_name'] == f_loc.res_top[line_sep['residue_name']]['C_TERMINAL']:
                            C_ter=[line_sep['x'],line_sep['y'],line_sep['z']]
                            C_resid=line_sep['residue_id']
                            C=True
                        try:
                        #### tries to make a N_terminal connecting atom variable
                            if line_sep['atom_name'] == f_loc.res_top[line_sep['residue_name']]['N_TERMINAL']:
                                N_resid=line_sep['residue_id']
                                N_ter=[line_sep['x'],line_sep['y'],line_sep['z']]
                                N=True
                        #### measures distance between N and C atoms. if the bond is over 3 A it counts as a new protein
                            dist=gen.calculate_distance(N_ter, C_ter)
                            if N and C and C_resid != N_resid and dist > 3.5:# and aas[line_sep['residue_name']] != sequence[chain_count][line_sep['residue_id']]:
                                N_ter, C_ter=False, False
                                ter_residues.append(line_sep['residue_id'])
                                chain_count+=1
                                atomistic_protein_input[chain_count]={} ### new chain key
                        except:
                            pass
                        prev_atom_coord = [line_sep['x'],line_sep['y'],line_sep['z']]
                        if line_sep['residue_id'] not in atomistic_protein_input[chain_count]:  ## if protein does not exist add to dict
                            atomistic_protein_input[chain_count][line_sep['residue_id']]={}
                    #### adds atom to dictionary, every atom is given a initial mass of zero 
                        atomistic_protein_input[chain_count][line_sep['residue_id']][line_sep['atom_number']]={'coord':np.array([line_sep['x'],line_sep['y'],line_sep['z']]),'atom':line_sep['atom_name'], 'res_type':line_sep['residue_name'],'frag_mass':0, 'resid':line_sep['residue_id']}
                    #### if atom is in the backbone list then its mass is updated to the correct one
                        if line_sep['atom_name'] in f_loc.res_top[line_sep['residue_name']]['ATOMS']:
                            if line_sep['atom_name'] in line_sep['atom_name'] in f_loc.res_top[line_sep['residue_name']]['atom_masses']:
                                atomistic_protein_input[chain_count][line_sep['residue_id']][line_sep['atom_number']]['frag_mass']=f_loc.res_top[line_sep['residue_name']]['atom_masses'][line_sep['atom_name']]    
    return atomistic_protein_input, chain_count+1    

def duplicate_chain():
    if len(g_var.duplicate) != 0:
        for ch_d in g_var.duplicate:
            duplicate = [int(x) for x in ch_d.split(':')]
            if len(duplicate) == 2 and duplicate[0] in g_var.atomistic_protein_input_raw:
                print('Using '+str(duplicate[1])+' copies of the atomistic chain '+str(duplicate[0]))
                for chain_duplication in range(duplicate[1]-1):
                    g_var.chain_count+=1
                    g_var.atomistic_protein_input_raw[g_var.chain_count]=copy.deepcopy(g_var.atomistic_protein_input_raw[duplicate[0]])
            else:
                sys.exit('your atomistic chain duplication input is incorrrect')   