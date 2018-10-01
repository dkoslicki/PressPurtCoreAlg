# For sanity purposes, let's implement the super naive version to determine sign stability
import numpy as np
import scipy.stats as st


def intervals(aij, x=0.01):
	"""
	This function defines an interval of size int_size around aij without changing the sign of aij
	:param aij: the (i,j) entry of a matrix (scalar)
	:param int_size: the size of the desired interval
	:return: an (ordered) list defining the endpoints of the interval
	"""
	if aij == 0:
		lower_bound = 0
		upper_bound = 0
	elif aij > 0:
		if x <= 2*aij:
			lower_bound = -x/2.
		elif x > 2*aij:
			lower_bound = -aij
		#lower_bound = np.piecewise(aij, [x <= 2*aij, x > 2*aij], [-x/2., -aij])
		if x <= 2*aij:
			upper_bound = x/2.
		elif x > 2*aij:
			upper_bound = x - aij
		#upper_bound = np.piecewise(aij, [x <= 2*aij, x >= 2*aij], [x/2., x - aij])
	elif aij < 0:
		if x <= 2*np.abs(aij):
			lower_bound = -x/2.
		elif x > 2*np.abs(aij):
			lower_bound = -x + np.abs(aij)
		#lower_bound = np.piecewise(aij, [x <= 2*np.abs(aij), x >= 2*np.abs(aij)], [-x/2., -x + np.abs(aij)])
		if x <= 2*np.abs(aij):
			upper_bound = x/2.
		elif x > 2*np.abs(aij):
			upper_bound = np.abs(aij)
		#upper_bound = np.piecewise(aij, [x <= 2*np.abs(aij), x >= 2*np.abs(aij)], [x/2., np.abs(aij)])
	return [lower_bound, upper_bound]


def is_stable(A):
	"""
	Check if the input matrix is asymptotically stable
	:param A: input matrix
	:return: Bool (1 iff asymptotically stable)
	"""
	[s, _] = np.linalg.eig(A)
	if all([np.real(i) < 0 for i in s]):
		return 1
	else:
		return 0


def get_entries_to_perturb(A):
	"""
	Returns a binary matrix indicating which entries to perturb
	:param A: input matrix (numpy or sympy matrix)
	:return: binary matrix of same dimensions as A
	"""
	m, n = A.shape
	res = np.zeros((m, n))
	for i in range(m):
		for j in range(n):
			if A[i, j] != 0:
				res[i, j] = 1
	return res


def exists_switch(Ainv, Apinv):
	"""
	Takes in a dictionary of with keys eps symbols string (use symbol.name), values the values they are to be evaluated at.
	Returns 1 if a switch has occurred, 0 otherwise
	:param eps_dict: dictionary {eps_symbols: eps_values}
	:return: 0 or 1
	"""
	(m, n) = Ainv.shape
	switch = 0
	for i in range(m):
		for j in range(n):
			if np.sign(Ainv[i, j]) != np.sign(Apinv[i, j]):
				switch = 1
				break
		if switch == 1:
			break
	return switch

# other tri diag
A = np.array([[-0.237, -1, 0, 0], [0.1, 0.015, -1, 0], [0, 0.1, -0.015, -1], [0, 0, 0.1, -0.015]])

# IGP
#A = np.array([[-0.237, -1, 0, 0], [0.1, -0.015, -1, -1], [0, 0.1, -0.015, -1], [0, .045, 0.1, -0.015]])

# Tri
#A = np.array([[-0.237, -1, 0, 0], [0.1, -0.015, -1, 0], [0, 0.1, -0.015, -1], [0, 0, 0.1, -0.015]])

Ainv = np.linalg.inv(A)
entries_to_pertub = get_entries_to_perturb(A)
m, n = A.shape

num_iterates = 10000
interval_length = 0.01

pert_array = np.zeros((m, n, num_iterates))
for i in range(m):
	for j in range(n):
		interval = intervals(A[i, j], interval_length)
		dist = st.uniform(interval[0], interval[1])
		vals = dist.rvs(num_iterates)
		pert_array[i, j, :] = vals

stable_counter = 0
switch_counter = 0
for it in range(num_iterates):
	Ap = np.array(A)
	for i in range(m):
		for j in range(n):
			Ap[i, j] += pert_array[i, j, it]
	Apinv = np.linalg.inv(Ap)
	is_switch = exists_switch(Ainv, Apinv)
	if is_stable(Ap):
		stable_counter += 1
		if is_switch:
			switch_counter += 1
print(switch_counter/float(stable_counter))

