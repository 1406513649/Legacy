import os
import sys
sys.path.insert(0, '../bin')
import trilinos as tt

def lists_are_same(a, b):
    return all([x in b for x in a] + [x in a for x in b])

def test_get_default_tpls():
    all_tpls = ['BLAS', 'LAPACK', 'Zlib', 'Netcdf', 'HDF5',
                'ParMETIS', 'Boost', 'BoostLib', 'SuperLU',
                'Scotch', 'Pthread', 'BinUtils', 'CSparse',
                'Matio', 'METIS']
    disabled_tpls = ['Pthread', 'BinUtils', 'CSparse', 'Matio', 'METIS']
    platform = 'linux'
    e, d = tt.get_default_tpls(None, platform)
    assert lists_are_same(d, disabled_tpls)
    assert lists_are_same(e, [x for x in all_tpls if x not in disabled_tpls])
    platform = 'darwin'
    disabled_tpls.append('Scotch')
    e, d = tt.get_default_tpls(None, platform)
    assert lists_are_same(d, disabled_tpls)
    assert lists_are_same(e, [x for x in all_tpls if x not in disabled_tpls])

def test_directory_utils():
    tt.create_directory('./foo_bar_01')
    assert os.path.isdir('./foo_bar_01')
    tt.remove('./foo_bar_01')
    assert not os.path.isdir('./foo_bar_01')

test_get_default_tpls()
test_directory_utils()
