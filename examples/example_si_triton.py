#! /usr/bin/env python

"""
Demonstrates the usage of pycp2k on Triton (computing cluster dedicated to
scientific computing at Aalto University)
"""

from pycp2k.cp2k import CP2K
from ase.lattice.cubic import Diamond
#import argparse

#===============================================================================
# The number of processes for MPI can be given in python as an argument when
# running this file. This is an example of how the arguments can be extracted
# in python.
#parser = argparse.ArgumentParser()
#parser.add_argument('-n', type=int, help='the number of MPI processes')
calc = CP2K()
calc.mpi_command = "srun --mpi=openmpi"
script_path = "/triton/becs/work/himanel1/masters/results"
project_name = "Si_bulk"
calc.input_path = script_path + "/" + project_name + ".inp"
calc.output_path = script_path + "/" + project_name + ".out"

#===============================================================================
# Structure
lattice = Diamond(directions=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                  symbol='Si',
                  latticeconstant=5.430697500,
                  size=(1, 1, 1))

#===============================================================================
# Shortcuts
CP2K_INPUT = calc.CP2K_INPUT
GLOBAL = CP2K_INPUT.GLOBAL
FORCE_EVAL = CP2K_INPUT.add_FORCE_EVAL()
SUBSYS = FORCE_EVAL.SUBSYS
DFT = FORCE_EVAL.DFT
SCF = DFT.SCF

#===============================================================================
# Input
GLOBAL.Run_type = "ENERGY_FORCE"
GLOBAL.Project = "Si_bulk8"
GLOBAL.Print_level = "LOW"

calc.create_cell(SUBSYS, lattice)
calc.create_coord(SUBSYS, lattice)

FORCE_EVAL.Method = "Quickstep"
FORCE_EVAL.PRINT.FORCES.Section_parameters = "ON"
DFT.Basis_set_file_name = "BASIS_SET"
DFT.Potential_file_name = "GTH_POTENTIALS"
DFT.QS.Eps_default = 1.0E-10
DFT.MGRID.Ngrids = 4
DFT.MGRID.Cutoff = 300
DFT.MGRID.Rel_cutoff = 60
DFT.XC.XC_FUNCTIONAL.Section_parameters = "PADE"
SCF.Scf_guess = "ATOMIC"
SCF.Eps_scf = 1.0E-7
SCF.Max_scf = 300
SCF.DIAGONALIZATION.Section_parameters = "ON"
SCF.DIAGONALIZATION.Algorithm = "STANDARD"
SCF.MIXING.Section_parameters = "T"
SCF.MIXING.Method = "BROYDEN_MIXING"
SCF.MIXING.Alpha = 0.4
SCF.MIXING.Nbroyden = 8
FORCE_EVAL.PRINT.FORCES.Section_parameters = "ON"

KIND = SUBSYS.add_KIND()
KIND.Section_parameters = "Si"
KIND.Element = "Si"
KIND.Basis_set = "DZVP-GTH-PADE"
KIND.Potential = "GTH-PADE-q4"

#===============================================================================
# Calculations
print calc.get_potential_energy()
