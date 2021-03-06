import argparse
import numpy as np
import os
import sys
import pickle
import timeit
from multiprocessing import Pool  # Much faster without dummy (threading)
import multiprocessing
import itertools

# import stuff in the src folder
try:
	import NumSwitch
except ImportError:
	sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
	import NumSwitch

def get_parser():
	parser = argparse.ArgumentParser(description="This script pre-processes a matrix by figuring out what the intervals of asymptotic stability are, as well as finding which perturbation values lead to a sign switch.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('input_file', type=str, help="Input comma separated file for the jacobian matrix.")
	parser.add_argument('output_folder', type=str, help="Output folder. A number of files will be created in the form 'output_folder/<prefix>_*.npy'")
	parser.add_argument('-p', '--prefix', help="Prefix of output files, if you so choose.", default=None)
	parser.add_argument('-m', '--max_bound', type=float, help="some of the matrices are unbounded stable towards one end, this is the limit the user imposes", default=10)
	parser.add_argument('-z', '--zero_perturb', action='store_true', help="Flag to indicated you want to pertub the zero entries.", default=False)
	parser.add_argument('-t', '--threads', type=int, help="Number of threads to use.", default=multiprocessing.cpu_count())
	parser.add_argument('-v', '--verbose', action='store_true', help='Include this flag if you want a couple messages printed to the screen as well.', default=False)
	return parser

if __name__ == '__main__':
	parser = get_parser()
	# read in the arguments
	args = parser.parse_args()
	verbose = args.verbose
	num_threads = int(args.threads)
	input_file = os.path.abspath(args.input_file)
	output_folder = args.output_folder
	if output_folder:
		output_folder = os.path.abspath(output_folder)
	prefix = args.prefix
	max_bound = float(args.max_bound)
	pert_zero = args.zero_perturb
	if not os.access(output_folder, os.W_OK):
		raise Exception("The provided directory %s is not writable." % output_folder)

	if prefix:
		asymp_stab_file = os.path.join(output_folder, prefix + "_asymptotic_stability.npy")
		num_switch_file = os.path.join(output_folder, prefix + "_num_switch_funcs.pkl")
		matrix_size_file = os.path.join(output_folder, prefix + "_size.npy")
		row_names_file = os.path.join(output_folder, prefix + "_row_names.txt")
		column_names_file = os.path.join(output_folder, prefix + "_column_names.txt")
		num_nonzero_file = os.path.join(output_folder, prefix + "_num_non_zero.npy")
	else:
		asymp_stab_file = os.path.join(output_folder, "asymptotic_stability.npy")
		num_switch_file = os.path.join(output_folder, "num_switch_funcs.pkl")
		matrix_size_file = os.path.join(output_folder, "size.npy")
		row_names_file = os.path.join(output_folder, "row_names.txt")
		column_names_file = os.path.join(output_folder, "column_names.txt")
		num_nonzero_file = os.path.join(output_folder, "num_non_zero.npy")

	# check for sanity of input parameters
	if not max_bound > 0:
		raise Exception("max_bound must be larger than 0; provided value: %d." % max_bound)

	# read in the input matrix
	#A = np.loadtxt(input_file, delimiter=",")
	A, row_names, column_names = NumSwitch.import_matrix(input_file)
	# save the row and column names
	with open(row_names_file, 'w') as fid:
		for item in row_names:
			fid.write("%s\n" % item)

	with open(column_names_file, 'w') as fid:
		for item in column_names:
			fid.write("%s\n" % item)

	# save the number of non-zero entries
	num_non_zero = len(np.where(A)[0])
	np.save(num_nonzero_file, num_non_zero)

	Ainv = np.linalg.inv(A)
	m, n = A.shape
	np.save(matrix_size_file, n)

	# make sure the original matrix is itself asymptotically stable
	if not NumSwitch.is_stable(A):
		raise Exception("Sorry, the input matrix is not stable itself (all eigenvalues must have negative real part). Please try again.")

	# compute the intervals of stability
	intervals = np.zeros((m, n, 2))
	def helper(k,l):
		val = NumSwitch.interval_of_stability(A, Ainv, k, l, max_bound=max_bound)
		return (val, k, l)
	def helper_star(arg):
		return helper(*arg)

	to_compute_args = []
	for k in range(m):
		for l in range(n):
			if A[k, l] != 0:
				#intervals[k, l, :] = NumSwitch.interval_of_stability(A, Ainv, k, l, max_bound=max_bound)
				to_compute_args.append((k, l))
			elif pert_zero:
				#intervals[k, l, :] = NumSwitch.interval_of_stability(A, Ainv, k, l, max_bound=max_bound)
				to_compute_args.append((k, l))
	# start the pool and do the computations
	pool = Pool(processes=num_threads)
	res = pool.map(helper_star, to_compute_args)
	# collect the results
	for val, k, l in res:
		intervals[k, l, :] = val

	# save these
	if verbose:
		print("Saving asymptotic stability to: %s" % asymp_stab_file)
	np.save(asymp_stab_file, intervals)

	# Compute the num switch functions
	# Looks like up to matrices of size 50, the parallelization doesn't help. NumSwitch.critical_epsilon is CPU non-intensive
	crit_epsilon_array = np.zeros((n, n, n, n))
	for k in range(n):
		for l in range(n):
			for i in range(n):
				for j in range(n):
					crit_epsilon_array[k, l, i, j] = NumSwitch.critical_epsilon(Ainv, k, l, i, j)

	num_switch_funcs = dict()
	# Looks like up to matrices of size 50, the parallelization doesn't help. Here again, the computation is CPU non-intensive
	for k in range(n):
		for l in range(n):
			if A[k, l] != 0:
				res = NumSwitch.num_switch_from_crit_eps(crit_epsilon_array, intervals, k, l)
				num_switch_funcs[k, l] = res
			elif pert_zero:
				res = NumSwitch.num_switch_from_crit_eps(crit_epsilon_array, intervals, k, l)
				num_switch_funcs[k, l] = res

	# Save it
	if verbose:
		print("Saving shape of num switch functions to: %s" % num_switch_file)
	fid = open(num_switch_file, 'wb')
	pickle.dump(num_switch_funcs, fid)
	fid.close()

	# This is a text format
	#for k in range(n):
	#	for l in range(n):
	#		key = (k, l)
	#		dict_val = num_switch_funcs[key]
	#		# TODO: switch based on zero entries
	#		fid.write("%d\t%d\t" % (key[0], key[1]))
	#		for i in range(len(dict_val) - 1):
	#			val, (start, stop) = dict_val[i]
	#			fid.write("%f\t%f\t%f\t" % (val, start, stop))
	#		if dict_val:
	#			val, (start, stop) = dict_val[-1]
	#			fid.write("%d\t%f\t%f\n" % (val, start, stop))
	#		else:
	#			fid.write("\n")
	#fid.close()
