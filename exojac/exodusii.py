import os
import sys
import imp
import numpy as np
from operator import mul
from mmap import mmap, ACCESS_READ
from numpy.compat import asbytes, asstr
from numpy import fromstring, ndarray, dtype, empty, array, asarray
from numpy import little_endian as LITTLE_ENDIAN

class Struct(object):
    pass


class NotYetImplemented(Exception):
    def __init__(self, meth):
        self.message = "{0}: ExodusIIFile method not yet implemented".format(meth)
        super(NotYetImplemented, self).__init__(self.message)


class ExodusIIFileError(Exception):
    pass


def ex_catstr(string, num):
    return "{0}{1}".format(string, num)


def ex_catstr2(string1, num1, string2, num2):
    return "{0}{1}{2}{3}".format(string1, num1, string2, num2)


def chara_to_text(chara, aslist=False):
    if chara.ndim == 1:
        return "".join(chara).strip()
    chara_as_text = ["".join(row).strip() for row in chara]
    if aslist:
        return chara_as_text
    return np.array(chara_as_text)


# ------------------------------------------------------------ exodusII.h --- #
EX_NOCLOBBER          =  0
EX_CLOBBER            =  1
EX_NORMAL_MODEL       =  2
EX_LARGE_MODEL        =  4
EX_NETCDF4            =  8
EX_NOSHARE            = 16
EX_SHARE              = 32

EX_READ               =  0
EX_WRITE              =  1

EX_ELEM_BLOCK         =  1
EX_NODE_SET           =  2
EX_SIDE_SET           =  3
EX_ELEM_MAP           =  4
EX_NODE_MAP           =  5
EX_EDGE_BLOCK         =  6
EX_EDGE_SET           =  7
EX_FACE_BLOCK         =  8
EX_FACE_SET           =  9
EX_ELEM_SET           = 10
EX_EDGE_MAP           = 11
EX_FACE_MAP           = 12
EX_GLOBAL             = 13
EX_NODE               = 15  # not defined in exodus
EX_EDGE               = 16  # not defined in exodus
EX_FACE               = 17  # not defined in exodus
EX_ELEM               = 18  # not defined in exodus

MAX_STR_LENGTH        =  32
MAX_VAR_NAME_LENGTH   =  20
MAX_LINE_LENGTH       =  80
MAX_ERR_LENGTH        =  256

EX_VERBOSE     = 1
EX_DEBUG       = 2
EX_ABORT       = 4

EX_INQ_FILE_TYPE       =  1  # inquire EXODUS II file type
EX_INQ_API_VERS        =  2  # inquire API version number
EX_INQ_DB_VERS         =  3  # inquire database version number
EX_INQ_TITLE           =  4  # inquire database title
EX_INQ_DIM             =  5  # inquire number of dimensions
EX_INQ_NODES           =  6  # inquire number of nodes
EX_INQ_ELEM            =  7  # inquire number of elements
EX_INQ_ELEM_BLK        =  8  # inquire number of element blocks
EX_INQ_NODE_SETS       =  9  # inquire number of node sets
EX_INQ_NS_NODE_LEN     = 10  # inquire length of node set node list
EX_INQ_SIDE_SETS       = 11  # inquire number of side sets
EX_INQ_SS_NODE_LEN     = 12  # inquire length of side set node list
EX_INQ_SS_ELEM_LEN     = 13  # inquire length of side set element list
EX_INQ_QA              = 14  # inquire number of QA records
EX_INQ_INFO            = 15  # inquire number of info records
EX_INQ_TIME            = 16  # inquire number of time steps in the database
EX_INQ_EB_PROP         = 17  # inquire number of element block properties
EX_INQ_NS_PROP         = 18  # inquire number of node set properties
EX_INQ_SS_PROP         = 19  # inquire number of side set properties
EX_INQ_NS_DF_LEN       = 20  # inquire length of node set distribution
                             # factor list
EX_INQ_SS_DF_LEN       = 21  # inquire length of side set distribution
                             # factor list
EX_INQ_LIB_VERS        = 22  # inquire API Lib vers number
EX_INQ_EM_PROP         = 23  # inquire number of element map properties
EX_INQ_NM_PROP         = 24  # inquire number of node map properties
EX_INQ_ELEM_MAP        = 25  # inquire number of element maps
EX_INQ_NODE_MAP        = 26  # inquire number of node maps
EX_INQ_EDGE            = 27  # inquire number of edges
EX_INQ_EDGE_BLK        = 28  # inquire number of edge blocks
EX_INQ_EDGE_SETS       = 29  # inquire number of edge sets
EX_INQ_ES_LEN          = 30  # inquire length of concat edge set edge list
EX_INQ_ES_DF_LEN       = 31  # inquire length of concat edge set dist
                             # factor list
EX_INQ_EDGE_PROP       = 32  # inquire number of properties stored per
                             # edge block
EX_INQ_ES_PROP         = 33  # inquire number of properties stored per edge set
EX_INQ_FACE            = 34  # inquire number of faces
EX_INQ_FACE_BLK        = 35  # inquire number of face blocks
EX_INQ_FACE_SETS       = 36  # inquire number of face sets
EX_INQ_FS_LEN          = 37  # inquire length of concat face set face list
EX_INQ_FS_DF_LEN       = 38  # inquire length of concat face set dist
                             # factor list
EX_INQ_FACE_PROP       = 39  # inquire number of properties stored per
                             # face block
EX_INQ_FS_PROP         = 40  # inquire number of properties stored per face set
EX_INQ_ELEM_SETS       = 41  # inquire number of element sets
EX_INQ_ELS_LEN         = 42  # inquire length of concat element set element list
EX_INQ_ELS_DF_LEN      = 43  # inquire length of concat element set dist
                             # factor list
EX_INQ_ELS_PROP        = 44  # inquire number of properties stored per elem set
EX_INQ_EDGE_MAP        = 45  # inquire number of edge maps
EX_INQ_FACE_MAP        = 46  # inquire number of face maps
EX_INQ_COORD_FRAMES    = 47  # inquire number of coordinate frames

# -------------------------------------------------------- exodusII_inc.h --- #
MAX_VAR_NAME_LENGTH = 20   # Internal use only

# Default "filesize" for newly created files.
# Set to 0 for normal filesize setting.
# Set to 1 for EXODUS_LARGE_MODEL setting to be the default
EXODUS_DEFAULT_SIZE = 1

# Exodus error return codes - function return values:
EX_FATAL = -1 # fatal error flag def
EX_NOERR =  0 # no error flag def
EX_WARN  =  1 # warning flag def

# This file contains defined constants that are used internally in the
# EXODUS II API.
#
# The first group of constants refer to netCDF variables, attributes, or
# dimensions in which the EXODUS II data are stored.  Using the defined
# constants will allow the names of the netCDF entities to be changed easily
# in the future if needed.  The first three letters of the constant identify
# the netCDF entity as a variable (VAR), dimension (DIM), or attribute (ATT).
#
# NOTE: The entity name should not have any blanks in it.  Blanks are
#       technically legal but some netcdf utilities (ncgen in particular)
#       fail when they encounter a blank in a name.
#
# DEFINED CONSTANT        ENTITY NAME     DATA STORED IN ENTITY
ATT_TITLE = "title" # the database title
ATT_API_VERSION = "api_version" # the EXODUS II api vers number
ATT_VERSION = "version" # the EXODUS II file vers number
ATT_FILESIZE = "file_size" # 1=large, 0=normal
ATT_FLT_WORDSIZE = "floating_point_word_size" # word size of floating
                                              # point numbers in file
ATT_FLT_WORDSIZE_BLANK = "floating point word size" # word size of floating
                                                    # point numbers in file
                                                    # used for db version 2.01
                                                    # and earlier
DIM_NUM_NODES = "num_nodes" # number of nodes
DIM_NUM_DIM = "num_dim" # number of dimensions; 2- or 3-d
DIM_NUM_EDGE = "num_edge" # number of edges (over all blks)
DIM_NUM_FACE = "num_face" # number of faces (over all blks)
DIM_NUM_ELEM = "num_elem" # number of elements
DIM_NUM_EL_BLK = "num_el_blk" # number of element blocks
DIM_NUM_ED_BLK = "num_ed_blk" # number of edge blocks
DIM_NUM_FA_BLK = "num_fa_blk" # number of face blocks

VAR_COORD = "coord" # nodal coordinates
VAR_COORD_X = "coordx" # X-dimension coordinate
VAR_COORD_Y = "coordy" # Y-dimension coordinate
VAR_COORD_Z = "coordz" # Z-dimension coordinate
VAR_NAME_COOR = "coor_names" # names of coordinates
VAR_NAME_EL_BLK = "eb_names" # names of element blocks
VAR_NAME_NS = "ns_names" # names of node sets
VAR_NAME_SS = "ss_names" # names of side sets
VAR_NAME_EM = "emap_names" # names of element maps
VAR_NAME_EDM = "edmap_names" # names of edge maps
VAR_NAME_FAM = "famap_names" # names of face maps
VAR_NAME_NM = "nmap_names" # names of node maps
VAR_NAME_ED_BLK = "ed_names" # names of edge blocks
VAR_NAME_FA_BLK = "fa_names" # names of face blocks
VAR_NAME_ES = "es_names" # names of edge sets
VAR_NAME_FS = "fs_names" # names of face sets
VAR_NAME_ELS = "els_names" # names of element sets
VAR_STAT_EL_BLK = "eb_status" # element block status
VAR_STAT_ECONN = "econn_status" # element block edge status
VAR_STAT_FCONN = "fconn_status" # element block face status
VAR_STAT_ED_BLK = "ed_status" # edge block status
VAR_STAT_FA_BLK = "fa_status" # face block status
VAR_ID_EL_BLK = "eb_prop1" # element block ids props
VAR_ID_ED_BLK = "ed_prop1" # edge block ids props
VAR_ID_FA_BLK = "fa_prop1" # face block ids props

ATT_NAME_ELB = "elem_type" # element type names for each element block

# number of elements in element block num
DIM_NUM_EL_IN_BLK = lambda num: ex_catstr("num_el_in_blk", num)

# number of nodes per element in element block num
DIM_NUM_NOD_PER_EL = lambda num: ex_catstr("num_nod_per_el", num)

# number of attributes in element block num
DIM_NUM_ATT_IN_BLK = lambda num: ex_catstr("num_att_in_blk", num)

# number of edges in edge block num
DIM_NUM_ED_IN_EBLK = lambda num: ex_catstr("num_ed_in_blk", num)

# number of nodes per edge in edge block num
DIM_NUM_NOD_PER_ED = lambda num: ex_catstr("num_nod_per_ed", num)

# number of edges per element in element block num
DIM_NUM_EDG_PER_EL = lambda num: ex_catstr("num_edg_per_el", num)

# number of attributes in edge block num
DIM_NUM_ATT_IN_EBLK = lambda num: ex_catstr("num_att_in_eblk", num)

# number of faces in face block num
DIM_NUM_FA_IN_FBLK = lambda num: ex_catstr("num_fa_in_blk", num)

# number of nodes per face in face block num
DIM_NUM_NOD_PER_FA = lambda num: ex_catstr("num_nod_per_fa", num)

# number of faces per element in element block num
DIM_NUM_FAC_PER_EL = lambda num: ex_catstr("num_fac_per_el", num)

# number of attributes in face block num
DIM_NUM_ATT_IN_FBLK = lambda num: ex_catstr("num_att_in_fblk", num)
DIM_NUM_ATT_IN_NBLK = "num_att_in_nblk"

# element connectivity for element block num
VAR_CONN = lambda num: ex_catstr("connect", num)

# array containing number of entity per entity for n-sided face/element blocks
VAR_EBEPEC = lambda num: ex_catstr("ebepecnt", num)

# list of attributes for element block num
VAR_ATTRIB = lambda num: ex_catstr("attrib", num)

# list of attribute names for element block num
VAR_NAME_ATTRIB = lambda num: ex_catstr("attrib_name", num)

# list of the numth property for all element blocks
VAR_EB_PROP = lambda num: ex_catstr("eb_prop", num)

# edge connectivity for element block num
VAR_ECONN = lambda num: ex_catstr("edgconn", num)

# edge connectivity for edge block num
VAR_EBCONN = lambda num: ex_catstr("ebconn", num)

# list of attributes for edge block num
VAR_EATTRIB = lambda num: ex_catstr("eattrb", num)
# list of attribute names for edge block num
VAR_NAME_EATTRIB = lambda num: ex_catstr("eattrib_name", num)

VAR_NATTRIB = "nattrb"
VAR_NAME_NATTRIB = "nattrib_name"
DIM_NUM_ATT_IN_NBLK = "num_att_in_nblk"
VAR_NSATTRIB = lambda num: ex_catstr("nsattrb", num)
VAR_NAME_NSATTRIB = lambda num: ex_catstr("nsattrib_name", num)
DIM_NUM_ATT_IN_NS = lambda num: ex_catstr("num_att_in_ns", num)
VAR_SSATTRIB = lambda num: ex_catstr("ssattrb", num)
VAR_NAME_SSATTRIB = lambda num: ex_catstr("ssattrib_name", num)
DIM_NUM_ATT_IN_SS = lambda num: ex_catstr("num_att_in_ss", num)
VAR_ESATTRIB = lambda num: ex_catstr("esattrb", num)
VAR_NAME_ESATTRIB = lambda num: ex_catstr("esattrib_name", num)
DIM_NUM_ATT_IN_ES = lambda num: ex_catstr("num_att_in_es", num)
VAR_FSATTRIB = lambda num: ex_catstr("fsattrb", num)
VAR_NAME_FSATTRIB = lambda num: ex_catstr("fsattrib_name", num)
DIM_NUM_ATT_IN_FS = lambda num: ex_catstr("num_att_in_fs", num)
VAR_ELSATTRIB = lambda num: ex_catstr("elsattrb", num)
VAR_NAME_ELSATTRIB = lambda num: ex_catstr("elsattrib_name", num)
DIM_NUM_ATT_IN_ELS = lambda num: ex_catstr("num_att_in_els", num)
VAR_ED_PROP = lambda num: ex_catstr("ed_prop", num)
                                           # list of the numth property
                                           # for all edge blocks
VAR_FCONN = lambda num: ex_catstr("facconn", num)
                                         # face connectivity for
                                         # element block num
VAR_FBCONN = lambda num: ex_catstr("fbconn", num)
                                         # face connectivity for
                                         # face block num
VAR_FBEPEC = lambda num: ex_catstr("fbepecnt", num)
                                           # array containing number of entity per
                                           # entity for n-sided face/element blocks
VAR_FATTRIB = lambda num: ex_catstr("fattrb", num)
                                          # list of attributes for
                                          # face block num
VAR_NAME_FATTRIB = lambda num: ex_catstr("fattrib_name", num)
                                                     # list of attribute names
                                                     # for face block num
VAR_FA_PROP = lambda num: ex_catstr("fa_prop", num)
                                           # list of the numth property
                                           # for all face blocks
ATT_PROP_NAME = "name" # name attached to element
                                                 # block, node set, side
                                                 # set, element map, or
                                                 # map properties
DIM_NUM_SS = "num_side_sets" # number of side sets
VAR_SS_STAT = "ss_status" # side set status
VAR_SS_IDS = "ss_prop1" # side set id properties
DIM_NUM_SIDE_SS = lambda num: ex_catstr("num_side_ss", num) # number of sides in
                                                           # side set num

DIM_NUM_DF_SS = lambda num: ex_catstr("num_df_ss", num) # number of distribution
                                                       # factors in side set num

# the distribution factors for each node in side set num
VAR_FACT_SS = lambda num: ex_catstr("dist_fact_ss", num)
VAR_ELEM_SS = lambda num: ex_catstr("elem_ss", num)
                                           # list of elements in side
                                           # set num
VAR_SIDE_SS = lambda num: ex_catstr("side_ss", num)
                                           # list of sides in side set
VAR_SS_PROP = lambda num: ex_catstr("ss_prop", num)
                                           # list of the numth property
                                           # for all side sets
DIM_NUM_ES = "num_edge_sets"# number of edge sets
VAR_ES_STAT = "es_status" # edge set status
VAR_ES_IDS = "es_prop1" # edge set id properties
DIM_NUM_EDGE_ES = lambda num: ex_catstr("num_edge_es", num)
                                                   # number of edges in edge set num
DIM_NUM_DF_ES = lambda num: ex_catstr("num_df_es", num)
                                               # number of distribution factors
                                               # in edge set num
VAR_FACT_ES = lambda num: ex_catstr("dist_fact_es", num)
                                                # the distribution factors
                                                # for each node in edge
                                                # set num
VAR_EDGE_ES = lambda num: ex_catstr("edge_es", num)
                                           # list of edges in edge
                                           # set num
VAR_ORNT_ES = lambda num: ex_catstr("ornt_es", num)
                                           # list of orientations in
                                           # the edge set.
VAR_ES_PROP = lambda num: ex_catstr("es_prop", num)
                                           # list of the numth property
                                           # for all edge sets
DIM_NUM_FS = "num_face_sets"# number of face sets
VAR_FS_STAT = "fs_status" # face set status
VAR_FS_IDS = "fs_prop1" # face set id properties
DIM_NUM_FACE_FS = lambda num: ex_catstr("num_face_fs", num)
                                                   # number of faces in side set num
DIM_NUM_DF_FS = lambda num: ex_catstr("num_df_fs", num)
                                               # number of distribution factors
                                               # in face set num
VAR_FACT_FS = lambda num: ex_catstr("dist_fact_fs", num)
                                                # the distribution factors
                                                # for each node in face
                                                # set num
VAR_FACE_FS = lambda num: ex_catstr("face_fs", num)
                                           # list of elements in face
                                           # set num
VAR_ORNT_FS = lambda num: ex_catstr("ornt_fs", num)
                                           # list of sides in side set
VAR_FS_PROP = lambda num: ex_catstr("fs_prop", num)
                                           # list of the numth property
                                           # for all face sets
DIM_NUM_ELS = "num_elem_sets"# number of elem sets
DIM_NUM_ELE_ELS = lambda num: ex_catstr("num_ele_els", num)
                                                   # number of elements in elem set
                                                   # num
DIM_NUM_DF_ELS = lambda num: ex_catstr("num_df_els", num)
                                                 # number of distribution factors
                                                 # in element set num
VAR_ELS_STAT = "els_status" # elem set status
VAR_ELS_IDS = "els_prop1" # elem set id properties
VAR_ELEM_ELS = lambda num: ex_catstr("elem_els", num)
                                             # list of elements in elem
                                             # set num
VAR_FACT_ELS = lambda num: ex_catstr("dist_fact_els", num)
                                                  # list of distribution
                                                  # factors in elem set num
VAR_ELS_PROP = lambda num: ex_catstr("els_prop", num)
                                             # list of the numth property
                                             # for all elem sets
DIM_NUM_NS = "num_node_sets"# number of node sets
DIM_NUM_NOD_NS = lambda num: ex_catstr("num_nod_ns", num)
                                                 # number of nodes in node set
                                                 # num
DIM_NUM_DF_NS = lambda num: ex_catstr("num_df_ns", num)
                                               # number of distribution factors
                                               # in node set num
VAR_NS_STAT = "ns_status" # node set status
VAR_NS_IDS = "ns_prop1" # node set id properties
VAR_NODE_NS = lambda num: ex_catstr("node_ns", num)
                                           # list of nodes in node set
                                           # num
VAR_FACT_NS = lambda num: ex_catstr("dist_fact_ns", num)
                                                # list of distribution
                                                # factors in node set num
VAR_NS_PROP = lambda num: ex_catstr("ns_prop", num)
                                           # list of the numth property
                                           # for all node sets
DIM_NUM_QA = "num_qa_rec" # number of QA records
VAR_QA_TITLE = "qa_records" # QA records
DIM_NUM_INFO = "num_info" # number of information records
VAR_INFO = "info_records" # information records
VAR_WHOLE_TIME = "time_whole" # simulation times for whole
                                                          # time steps
VAR_ELEM_TAB = "elem_var_tab" # element variable truth
                                                      # table
VAR_EBLK_TAB = "edge_var_tab" # edge variable truth table
VAR_FBLK_TAB = "face_var_tab" # face variable truth table
VAR_ELSET_TAB = "elset_var_tab" # elemset variable truth
                                                        # table
VAR_SSET_TAB = "sset_var_tab" # sideset variable truth
                                                      # table
VAR_FSET_TAB = "fset_var_tab" # faceset variable truth
                                                      # table
VAR_ESET_TAB = "eset_var_tab" # edgeset variable truth
                                                      # table
VAR_NSET_TAB = "nset_var_tab" # nodeset variable truth
                                                      # table
DIM_NUM_GLO_VAR = "num_glo_var" # number of global variables
VAR_NAME_GLO_VAR = "name_glo_var" # names of global variables
VAR_GLO_VAR = "vals_glo_var" # values of global variables
DIM_NUM_NOD_VAR = "num_nod_var" # number of nodal variables
VAR_NAME_NOD_VAR = "name_nod_var" # names of nodal variables
VAR_NOD_VAR = "vals_nod_var" # values of nodal variables

# values of nodal variables
VAR_NOD_VAR_NEW = lambda num: ex_catstr("vals_nod_var", num)

DIM_NUM_ELE_VAR = "num_elem_var" # number of element variables
VAR_NAME_ELE_VAR = "name_elem_var" # names of element variables
# values of element variable num1 in element block num2
VAR_ELEM_VAR = lambda num1, num2: ex_catstr2("vals_elem_var", num1, "eb", num2)

# values of edge variable num1 in edge block num2
DIM_NUM_EDG_VAR = "num_edge_var" # number of edge variables
VAR_NAME_EDG_VAR = "name_edge_var" # names of edge variables
VAR_EDGE_VAR = lambda num1, num2: ex_catstr2("vals_edge_var", num1, "eb", num2)

# values of face variable num1 in face block num2
DIM_NUM_FAC_VAR = "num_face_var" # number of face variables
VAR_NAME_FAC_VAR = "name_face_var" # names of face variables
VAR_FACE_VAR = lambda num1, num2: ex_catstr2("vals_face_var", num1,"fb", num2)

# values of nodeset variable num1 in nodeset num2
DIM_NUM_NSET_VAR = "num_nset_var" # number of nodeset variables
VAR_NAME_NSET_VAR = "name_nset_var" # names of nodeset variables
VAR_NS_VAR = lambda num1, num2: ex_catstr2("vals_nset_var", num1,"ns", num2)

# values of edgeset variable num1 in edgeset num2
DIM_NUM_ESET_VAR = "num_eset_var" # number of edgeset variables
VAR_NAME_ESET_VAR = "name_eset_var" # names of edgeset variables
VAR_ES_VAR = lambda num1, num2: ex_catstr2("vals_eset_var", num1,"es", num2)

# values of faceset variable num1 in faceset num2
DIM_NUM_FSET_VAR = "num_fset_var" # number of faceset variables
VAR_NAME_FSET_VAR = "name_fset_var" # names of faceset variables
VAR_FS_VAR = lambda num1, num2: ex_catstr2("vals_fset_var", num1,"fs", num2)

# values of sideset variable num1 in sideset num2
DIM_NUM_SSET_VAR = "num_sset_var" # number of sideset variables
VAR_NAME_SSET_VAR = "name_sset_var" # names of sideset variables
VAR_SS_VAR = lambda num1, num2: ex_catstr2("vals_sset_var", num1,"ss", num2)

# values of elemset variable num1 in elemset num2
DIM_NUM_ELSET_VAR = "num_elset_var" # number of element set variables
VAR_NAME_ELSET_VAR = "name_elset_var"# names of elemset variables
VAR_ELS_VAR = lambda num1, num2: ex_catstr2("vals_elset_var", num1,"es", num2)

# general dimension of length MAX_STR_LENGTH used for name lengths
DIM_STR = "len_string"

# general dimension of length MAX_LINE_LENGTH used for long strings
DIM_LIN = "len_line"
DIM_N4 = "four" # general dimension of length 4

# unlimited (expandable) dimension for time steps
DIM_TIME = "time_step"

DIM_NUM_EM = "num_elem_maps" # number of element maps
VAR_ELEM_MAP = lambda num: ex_catstr("elem_map", num) # the numth element map
VAR_EM_PROP = lambda num: ex_catstr("em_prop", num) # list of the numth property
                                                    # for all element maps

DIM_NUM_EDM = "num_edge_maps" # number of edge maps
VAR_EDGE_MAP = lambda num: ex_catstr("edge_map", num) # the numth edge map
VAR_EDM_PROP = lambda num: ex_catstr("edm_prop", num) # list of the numth property
                                                     # for all edge maps

DIM_NUM_FAM = "num_face_maps" # number of face maps
VAR_FACE_MAP = lambda num: ex_catstr("face_map", num) # the numth face map
VAR_FAM_PROP = lambda num: ex_catstr("fam_prop", num) # list of the numth property
                                                     # for all face maps

DIM_NUM_NM = "num_node_maps" # number of node maps
VAR_NODE_MAP = lambda num: ex_catstr("node_map", num) # the numth node map
VAR_NM_PROP = lambda num: ex_catstr("nm_prop", num) # list of the numth property
                                                   # for all node maps

DIM_NUM_CFRAMES = "num_cframes"
DIM_NUM_CFRAME9 = "num_cframes_9"
VAR_FRAME_COORDS = "frame_coordinates"
VAR_FRAME_IDS = "frame_ids"
VAR_FRAME_TAGS = "frame_tags"

EX_EL_UNK = -1,     # unknown entity
EX_EL_NULL_ELEMENT = 0
EX_EL_TRIANGLE =   1  # Triangle entity
EX_EL_QUAD =   2  # Quad entity
EX_EL_HEX =   3  # Hex entity
EX_EL_WEDGE =   4  # Wedge entity
EX_EL_TETRA =   5  # Tetra entity
EX_EL_TRUSS =   6  # Truss entity
EX_EL_BEAM =   7  # Beam entity
EX_EL_SHELL =   8  # Shell entity
EX_EL_SPHERE =   9  # Sphere entity
EX_EL_CIRCLE =  10  # Circle entity
EX_EL_TRISHELL =  11  # Triangular Shell entity
EX_EL_PYRAMID =  12  # Pyramid entity
ex_element_type = {
    EX_EL_UNK: EX_EL_UNK,
    EX_EL_NULL_ELEMENT: EX_EL_NULL_ELEMENT,
    EX_EL_TRIANGLE: EX_EL_TRIANGLE,
    EX_EL_QUAD: EX_EL_QUAD,
    EX_EL_HEX: EX_EL_HEX,
    EX_EL_WEDGE: EX_EL_WEDGE,
    EX_EL_TETRA: EX_EL_TETRA,
    EX_EL_TRUSS: EX_EL_TRUSS,
    EX_EL_BEAM: EX_EL_BEAM,
    EX_EL_SHELL: EX_EL_SHELL,
    EX_EL_SPHERE: EX_EL_SPHERE,
    EX_EL_CIRCLE: EX_EL_CIRCLE,
    EX_EL_TRISHELL: EX_EL_TRISHELL,
    EX_EL_PYRAMID: EX_EL_PYRAMID
    }

EX_CF_RECTANGULAR = 1
EX_CF_CYLINDRICAL = 2
EX_CF_SPHERICAL = 3
ex_coordinate_frame_type = {
    EX_CF_RECTANGULAR: EX_CF_RECTANGULAR,
    EX_CF_CYLINDRICAL: EX_CF_CYLINDRICAL,
    EX_CF_SPHERICAL: EX_CF_SPHERICAL
}

elem_blk_parm = Struct()
elem_blk_parm.elem_type = None
elem_blk_parm.elem_blk_id = None
elem_blk_parm.num_elem_in_blk = None
elem_blk_parm.num_nodes_per_elem = None
elem_blk_parm.num_sides = None
elem_blk_parm.num_nodes_per_side = None
elem_blk_parm.num_attr = None
elem_blk_parm.elem_ctr = None

# ------------------------------------------------------------ exofile.py --- #
ATT_FILENAME = "filename"
ATT_RUNID = "runid"
DTYPE_FLT = "f"
DTYPE_INT = "i"
DTYPE_TXT = "c"

PX_VAR_EL_MAP = "elem_map"
PX_VAR_COORDS = lambda i: ex_catstr(VAR_COORD, {0: "x", 1: "y", 2: "z"}[i])
PX_DIM_VARS = lambda s: {"G": DIM_NUM_GLO_VAR, "N": DIM_NUM_NOD_VAR,
                         "E": DIM_NUM_ELE_VAR, "M": DIM_NUM_NSET_VAR,
                         "S": DIM_NUM_SSET_VAR}[s.upper()]
PX_VAR_NAMES = lambda s: {"G": VAR_NAME_GLO_VAR, "N": VAR_NAME_NOD_VAR,
                          "E": VAR_NAME_ELE_VAR, "M": VAR_NAME_NSET_VAR,
                          "S": VAR_NAME_SSET_VAR}[s.upper()]
PX_VAR_GLO = "G"
PX_VAR_NOD = "N"
PX_VAR_ELE = "E"
PX_VAR_NS = "M"
PX_VAR_SS = "S"
PX_ELEM_BLK = "EB"
PX_NODE_SET = "NS"
PX_SIDE_SET = "SS"
PX_X_COMP  = 0
PX_Y_COMP  = 1
PX_Z_COMP  = 2
PX_OFFSET = 1
PX_HUGE = 1.E+99

def PX_PROPINFO(obj_type):
    if obj_type == EX_ELEM_BLOCK:
        return VAR_EB_PROP, DIM_NUM_EL_BLK
    if obj_type == EX_FACE_BLOCK:
        return VAR_FA_PROP, DIM_NUM_FA_BLK
    if obj_type == EX_EDGE_BLOCK:
        return VAR_ED_PROP, DIM_NUM_ED_BLK
    if obj_type == EX_NODE_SET:
        return VAR_NS_PROP, DIM_NUM_NS
    if obj_type == EX_SIDE_SET:
        return VAR_SS_PROP, DIM_NUM_SS
    if obj_type == EX_EDGE_SET:
        return VAR_ES_PROP, DIM_NUM_EDGE_ES
    if obj_type == EX_FACE_SET:
        return VAR_FS_PROP, DIM_NUM_FACE_FS
    if obj_type == EX_ELEM_SET:
        return VAR_ELS_PROP, DIM_NUM_ELS
    if obj_type == EX_ELEM_MAP:
        return VAR_EM_PROP, DIM_NUM_EM
    if obj_type == EX_FACE_MAP:
        return VAR_FAM_PROP, DIM_NUM_FAM
    if obj_type == EX_EDGE_MAP:
        return VAR_EDM_PROP, DIM_NUM_EDM
    if obj_type == EX_NODE_MAP:
        return VAR_NM_PROP, DIM_NUM_NM
    raise ExodusIIFileError("{0}: unrecognized obj_type".format(obj_type))
"""
NetCDF reader/writer module.

This module is used to read and create NetCDF files. NetCDF files are
accessed through the `netcdf_file` object. Data written to and from NetCDF
files are contained in `netcdf_variable` objects. Attributes are given
as member variables of the `netcdf_file` and `netcdf_variable` objects.

Notes
-----
NetCDF files are a self-describing binary data format. The file contains
metadata that describes the dimensions and variables in the file. More
details about NetCDF files can be found `here
<http://www.unidata.ucar.edu/software/netcdf/docs/netcdf.html>`_. There
are three main sections to a NetCDF data structure:

1. Dimensions
2. Variables
3. Attributes

The dimensions section records the name and length of each dimension used
by the variables. The variables would then indicate which dimensions it
uses and any attributes such as data units, along with containing the data
values for the variable. It is good practice to include a
variable that is the same name as a dimension to provide the values for
that axes. Lastly, the attributes section would contain additional
information such as the name of the file creator or the instrument used to
collect the data.

When writing data to a NetCDF file, there is often the need to indicate the
'record dimension'. A record dimension is the unbounded dimension for a
variable. For example, a temperature variable may have dimensions of
latitude, longitude and time. If one wants to add more temperature data to
the NetCDF file as time progresses, then the temperature variable should
have the time dimension flagged as the record dimension.

This module implements the Scientific.IO.NetCDF API to read and create
NetCDF files. The same API is also used in the PyNIO and pynetcdf
modules, allowing these modules to be used interchangeably when working
with NetCDF files. The major advantage of this module over other
modules is that it doesn't require the code to be linked to the NetCDF
libraries.

In addition, the NetCDF file header contains the position of the data in
the file, so access can be done in an efficient manner without loading
unnecessary data into memory. It uses the ``mmap`` module to create
Numpy arrays mapped to the data on disk, for the same purpose.

Examples
--------
To create a NetCDF file:

    >>> from scipy.io import netcdf
    >>> f = netcdf.netcdf_file('simple.nc', 'w')
    >>> f.history = 'Created for a test'
    >>> f.createDimension('time', 10)
    >>> time = f.createVariable('time', 'i', ('time',))
    >>> time[:] = range(10)
    >>> time.units = 'days since 2008-01-01'
    >>> f.close()

Note the assignment of ``range(10)`` to ``time[:]``.  Exposing the slice
of the time variable allows for the data to be set in the object, rather
than letting ``range(10)`` overwrite the ``time`` variable.

To read the NetCDF file we just created:

    >>> from scipy.io import netcdf
    >>> f = netcdf.netcdf_file('simple.nc', 'r')
    >>> print f.history
    Created for a test
    >>> time = f.variables['time']
    >>> print time.units
    days since 2008-01-01
    >>> print time.shape
    (10,)
    >>> print time[-1]
    9
    >>> f.close()

"""

#TODO:
# * properly implement ``_FillValue``.
# * implement Jeff Whitaker's patch for masked variables.
# * fix character variables.
# * implement PAGESIZE for Python 2.6?

#The Scientific.IO.NetCDF API allows attributes to be added directly to
#instances of ``netcdf_file`` and ``netcdf_variable``. To differentiate
#between user-set attributes and instance attributes, user-set attributes
#are automatically stored in the ``_attributes`` attribute by overloading
#``__setattr__``. This is the reason why the code sometimes uses
#``obj.__dict__['key'] = value``, instead of simply ``obj.key = value``;
#otherwise the key would be inserted into userspace attributes.
ABSENT       = asbytes('\x00\x00\x00\x00\x00\x00\x00\x00')
ZERO         = asbytes('\x00\x00\x00\x00')
NC_BYTE      = asbytes('\x00\x00\x00\x01')
NC_CHAR      = asbytes('\x00\x00\x00\x02')
NC_SHORT     = asbytes('\x00\x00\x00\x03')
NC_INT       = asbytes('\x00\x00\x00\x04')
NC_FLOAT     = asbytes('\x00\x00\x00\x05')
NC_DOUBLE    = asbytes('\x00\x00\x00\x06')
NC_DIMENSION = asbytes('\x00\x00\x00\n')
NC_VARIABLE  = asbytes('\x00\x00\x00\x0b')
NC_ATTRIBUTE = asbytes('\x00\x00\x00\x0c')


TYPEMAP = { NC_BYTE:   ('b', 1),
            NC_CHAR:   ('c', 1),
            NC_SHORT:  ('h', 2),
            NC_INT:    ('i', 4),
            NC_FLOAT:  ('f', 4),
            NC_DOUBLE: ('d', 8) }

REVERSE = { ('b', 1): NC_BYTE,
            ('B', 1): NC_CHAR,
            ('c', 1): NC_CHAR,
            ('h', 2): NC_SHORT,
            ('i', 4): NC_INT,
            ('f', 4): NC_FLOAT,
            ('d', 8): NC_DOUBLE,

            # these come from asarray(1).dtype.char and asarray('foo').dtype.char,
            # used when getting the types from generic attributes.
            ('l', 4): NC_INT,
            ('S', 1): NC_CHAR }


class netcdf_file(object):
    """
    A file object for NetCDF data.

    A `netcdf_file` object has two standard attributes: `dimensions` and
    `variables`. The values of both are dictionaries, mapping dimension
    names to their associated lengths and variable names to variables,
    respectively. Application programs should never modify these
    dictionaries.

    All other attributes correspond to global attributes defined in the
    NetCDF file. Global file attributes are created by assigning to an
    attribute of the `netcdf_file` object.

    Parameters
    ----------
    filename : string or file-like
        string -> filename
    mode : {'r', 'w'}, optional
        read-write mode, default is 'r'
    mmap : None or bool, optional
        Whether to mmap `filename` when reading.  Default is True
        when `filename` is a file name, False when `filename` is a
        file-like object
    version : {1, 2}, optional
        version of netcdf to read / write, where 1 means *Classic
        format* and 2 means *64-bit offset format*.  Default is 1.  See
        `here <http://www.unidata.ucar.edu/software/netcdf/docs/netcdf/Which-Format.html>`_
        for more info.

    """
    def __init__(self, filename, mode='r', mmap=None, version=1):
        """Initialize netcdf_file from fileobj (str or file-like)."""
        if hasattr(filename, 'seek'): # file-like
            self.fp = filename
            self.filename = 'None'
            if mmap is None:
                mmap = False
            elif mmap and not hasattr(filename, 'fileno'):
                raise ValueError('Cannot use file object for mmap')
        else: # maybe it's a string
            self.filename = filename
            self.fp = open(self.filename, '%sb' % mode)
            if mmap is None:
                mmap  = True
        self.use_mmap = mmap
        self.version_byte = version

        if not mode in 'rw':
            raise ValueError("Mode must be either 'r' or 'w'.")
        self.mode = mode

        self.dimensions = {}
        self.variables = {}

        self._dims = []
        self._recs = 0
        self._recsize = 0

        self._attributes = {}

        if mode == 'r':
            self._read()

    def __setattr__(self, attr, value):
        # Store user defined attributes in a separate dict,
        # so we can save them to file later.
        try:
            self._attributes[attr] = value
        except AttributeError:
            pass
        self.__dict__[attr] = value

    def close(self):
        """Closes the NetCDF file."""
        if not self.fp.closed:
            try:
                self.flush()
            finally:
                self.fp.close()
    __del__ = close

    def createDimension(self, name, length):
        """
        Adds a dimension to the Dimension section of the NetCDF data structure.

        Note that this function merely adds a new dimension that the variables can
        reference.  The values for the dimension, if desired, should be added as
        a variable using `createVariable`, referring to this dimension.

        Parameters
        ----------
        name : str
            Name of the dimension (Eg, 'lat' or 'time').
        length : int
            Length of the dimension.

        See Also
        --------
        createVariable

        """
        self.dimensions[name] = length
        self._dims.append(name)

    def createVariable(self, name, type, dimensions):
        """
        Create an empty variable for the `netcdf_file` object, specifying its data
        type and the dimensions it uses.

        Parameters
        ----------
        name : str
            Name of the new variable.
        type : dtype or str
            Data type of the variable.
        dimensions : sequence of str
            List of the dimension names used by the variable, in the desired order.

        Returns
        -------
        variable : netcdf_variable
            The newly created ``netcdf_variable`` object.
            This object has also been added to the `netcdf_file` object as well.

        See Also
        --------
        createDimension

        Notes
        -----
        Any dimensions to be used by the variable should already exist in the
        NetCDF data structure or should be created by `createDimension` prior to
        creating the NetCDF variable.

        """
        shape = tuple([self.dimensions[dim] for dim in dimensions])
        shape_ = tuple([dim or 0 for dim in shape])  # replace None with 0 for numpy

        if isinstance(type, basestring): type = dtype(type)
        typecode, size = type.char, type.itemsize
        if (typecode, size) not in REVERSE:
            raise ValueError("NetCDF 3 does not support type %s" % type)
        dtype_ = '>%s' % typecode
        if size > 1: dtype_ += str(size)

        data = empty(shape_, dtype=dtype_)
        self.variables[name] = netcdf_variable(data, typecode, size, shape, dimensions)
        return self.variables[name]

    def flush(self):
        """
        Perform a sync-to-disk flush if the `netcdf_file` object is in write mode.

        See Also
        --------
        sync : Identical function

        """
        if hasattr(self, 'mode') and self.mode is 'w':
            self._write()
    sync = flush

    def _write(self):
        self.fp.write(asbytes('CDF'))
        self.fp.write(array(self.version_byte, '>b').tostring())

        # Write headers and data.
        self._write_numrecs()
        self._write_dim_array()
        self._write_gatt_array()
        self._write_var_array()

    def _write_numrecs(self):
        # Get highest record count from all record variables.
        for var in self.variables.values():
            if var.isrec and len(var.data) > self._recs:
                self.__dict__['_recs'] = len(var.data)
        self._pack_int(self._recs)

    def _write_dim_array(self):
        if self.dimensions:
            self.fp.write(NC_DIMENSION)
            self._pack_int(len(self.dimensions))
            for name in self._dims:
                self._pack_string(name)
                length = self.dimensions[name]
                self._pack_int(length or 0)  # replace None with 0 for record dimension
        else:
            self.fp.write(ABSENT)

    def _write_gatt_array(self):
        self._write_att_array(self._attributes)

    def _write_att_array(self, attributes):
        if attributes:
            self.fp.write(NC_ATTRIBUTE)
            self._pack_int(len(attributes))
            for name, values in attributes.items():
                self._pack_string(name)
                self._write_values(values)
        else:
            self.fp.write(ABSENT)

    def _write_var_array(self):
        if self.variables:
            self.fp.write(NC_VARIABLE)
            self._pack_int(len(self.variables))

            # Sort variables non-recs first, then recs. We use a DSU
            # since some people use pupynere with Python 2.3.x.
            deco = [ (v._shape and not v.isrec, k) for (k, v) in self.variables.items() ]
            deco.sort()
            variables = [ k for (unused, k) in deco ][::-1]

            # Set the metadata for all variables.
            for name in variables:
                self._write_var_metadata(name)
            # Now that we have the metadata, we know the vsize of
            # each record variable, so we can calculate recsize.
            self.__dict__['_recsize'] = sum([
                    var._vsize for var in self.variables.values()
                    if var.isrec])
            # Set the data for all variables.
            for name in variables:
                self._write_var_data(name)
        else:
            self.fp.write(ABSENT)

    def _write_var_metadata(self, name):
        var = self.variables[name]

        self._pack_string(name)
        self._pack_int(len(var.dimensions))
        for dimname in var.dimensions:
            dimid = self._dims.index(dimname)
            self._pack_int(dimid)

        self._write_att_array(var._attributes)

        nc_type = REVERSE[var.typecode(), var.itemsize()]
        self.fp.write(asbytes(nc_type))

        if not var.isrec:
            vsize = var.data.size * var.data.itemsize
            vsize += -vsize % 4
        else:  # record variable
            try:
                vsize = var.data[0].size * var.data.itemsize
            except IndexError:
                vsize = 0
            rec_vars = len([var for var in self.variables.values()
                    if var.isrec])
            if rec_vars > 1:
                vsize += -vsize % 4
        self.variables[name].__dict__['_vsize'] = vsize
        self._pack_int(vsize)

        # Pack a bogus begin, and set the real value later.
        self.variables[name].__dict__['_begin'] = self.fp.tell()
        self._pack_begin(0)

    def _write_var_data(self, name):
        var = self.variables[name]

        # Set begin in file header.
        the_beguine = self.fp.tell()
        self.fp.seek(var._begin)
        self._pack_begin(the_beguine)
        self.fp.seek(the_beguine)

        # Write data.
        if not var.isrec:
            self.fp.write(var.data.tostring())
            count = var.data.size * var.data.itemsize
            self.fp.write(asbytes('0') * (var._vsize - count))
        else:  # record variable
            # Handle rec vars with shape[0] < nrecs.
            if self._recs > len(var.data):
                shape = (self._recs,) + var.data.shape[1:]
                var.data.resize(shape)

            pos0 = pos = self.fp.tell()
            for rec in var.data:
                # Apparently scalars cannot be converted to big endian. If we
                # try to convert a ``=i4`` scalar to, say, '>i4' the dtype
                # will remain as ``=i4``.
                if not rec.shape and (rec.dtype.byteorder == '<' or
                        (rec.dtype.byteorder == '=' and LITTLE_ENDIAN)):
                    rec = rec.byteswap()
                self.fp.write(rec.tostring())
                # Padding
                count = rec.size * rec.itemsize
                self.fp.write(asbytes('0') * (var._vsize - count))
                pos += self._recsize
                self.fp.seek(pos)
            self.fp.seek(pos0 + var._vsize)

    def _write_values(self, values):
        if hasattr(values, 'dtype'):
            nc_type = REVERSE[values.dtype.char, values.dtype.itemsize]
        else:
            types = [
                    (int, NC_INT),
                    (long, NC_INT),
                    (float, NC_FLOAT),
                    (basestring, NC_CHAR),
                    ]
            try:
                sample = values[0]
            except TypeError:
                sample = values
            for class_, nc_type in types:
                if isinstance(sample, class_): break

        typecode, size = TYPEMAP[nc_type]
        dtype_ = '>%s' % typecode

        values = asarray(values, dtype=dtype_)

        self.fp.write(asbytes(nc_type))

        if values.dtype.char == 'S':
            nelems = values.itemsize
        else:
            nelems = values.size
        self._pack_int(nelems)

        if not values.shape and (values.dtype.byteorder == '<' or
                (values.dtype.byteorder == '=' and LITTLE_ENDIAN)):
            values = values.byteswap()
        self.fp.write(values.tostring())
        count = values.size * values.itemsize
        self.fp.write(asbytes('0') * (-count % 4))  # pad

    def _read(self):
        # Check magic bytes and version
        magic = self.fp.read(3)
        if not magic == asbytes('CDF'):
            raise TypeError("Error: %s is not a valid NetCDF 3 file" %
                            self.filename)
        self.__dict__['version_byte'] = fromstring(self.fp.read(1), '>b')[0]

        # Read file headers and set data.
        self._read_numrecs()
        self._read_dim_array()
        self._read_gatt_array()
        self._read_var_array()

    def _read_numrecs(self):
        self.__dict__['_recs'] = self._unpack_int()

    def _read_dim_array(self):
        header = self.fp.read(4)
        if not header in [ZERO, NC_DIMENSION]:
            raise ValueError("Unexpected header.")
        count = self._unpack_int()

        for dim in range(count):
            name = asstr(self._unpack_string())
            length = self._unpack_int() or None  # None for record dimension
            self.dimensions[name] = length
            self._dims.append(name)  # preserve order

    def _read_gatt_array(self):
        for k, v in self._read_att_array().items():
            self.__setattr__(k, v)

    def _read_att_array(self):
        header = self.fp.read(4)
        if not header in [ZERO, NC_ATTRIBUTE]:
            raise ValueError("Unexpected header.")
        count = self._unpack_int()

        attributes = {}
        for attr in range(count):
            name = asstr(self._unpack_string())
            attributes[name] = self._read_values()
        return attributes

    def _read_var_array(self):
        header = self.fp.read(4)
        if not header in [ZERO, NC_VARIABLE]:
            raise ValueError("Unexpected header.")

        begin = 0
        dtypes = {'names': [], 'formats': []}
        rec_vars = []
        count = self._unpack_int()
        for var in range(count):
            (name, dimensions, shape, attributes,
             typecode, size, dtype_, begin_, vsize) = self._read_var()
            # http://www.unidata.ucar.edu/software/netcdf/docs/netcdf.html
            # Note that vsize is the product of the dimension lengths
            # (omitting the record dimension) and the number of bytes
            # per value (determined from the type), increased to the
            # next multiple of 4, for each variable. If a record
            # variable, this is the amount of space per record. The
            # netCDF "record size" is calculated as the sum of the
            # vsize's of all the record variables.
            #
            # The vsize field is actually redundant, because its value
            # may be computed from other information in the header. The
            # 32-bit vsize field is not large enough to contain the size
            # of variables that require more than 2^32 - 4 bytes, so
            # 2^32 - 1 is used in the vsize field for such variables.
            if shape and shape[0] is None: # record variable
                rec_vars.append(name)
                # The netCDF "record size" is calculated as the sum of
                # the vsize's of all the record variables.
                self.__dict__['_recsize'] += vsize
                if begin == 0: begin = begin_
                dtypes['names'].append(name)
                dtypes['formats'].append(str(shape[1:]) + dtype_)

                # Handle padding with a virtual variable.
                if typecode in 'bch':
                    actual_size = reduce(mul, (1,) + shape[1:]) * size
                    padding = -actual_size % 4
                    if padding:
                        dtypes['names'].append('_padding_%d' % var)
                        dtypes['formats'].append('(%d,)>b' % padding)

                # Data will be set later.
                data = None
            else: # not a record variable
                # Calculate size to avoid problems with vsize (above)
                a_size = reduce(mul, shape, 1) * size
                if self.use_mmap:
                    mm = mmap(self.fp.fileno(), begin_+a_size, access=ACCESS_READ)
                    data = ndarray.__new__(ndarray, shape, dtype=dtype_,
                            buffer=mm, offset=begin_, order=0)
                else:
                    pos = self.fp.tell()
                    self.fp.seek(begin_)
                    data = fromstring(self.fp.read(a_size), dtype=dtype_)
                    data.shape = shape
                    self.fp.seek(pos)

            # Add variable.
            self.variables[name] = netcdf_variable(
                    data, typecode, size, shape, dimensions, attributes)

        if rec_vars:
            # Remove padding when only one record variable.
            if len(rec_vars) == 1:
                dtypes['names'] = dtypes['names'][:1]
                dtypes['formats'] = dtypes['formats'][:1]

            # Build rec array.
            if self.use_mmap:
                mm = mmap(self.fp.fileno(), begin+self._recs*self._recsize, access=ACCESS_READ)
                rec_array = ndarray.__new__(ndarray, (self._recs,), dtype=dtypes,
                        buffer=mm, offset=begin, order=0)
            else:
                pos = self.fp.tell()
                self.fp.seek(begin)
                rec_array = fromstring(self.fp.read(self._recs*self._recsize), dtype=dtypes)
                rec_array.shape = (self._recs,)
                self.fp.seek(pos)

            for var in rec_vars:
                self.variables[var].__dict__['data'] = rec_array[var]

    def _read_var(self):
        name = asstr(self._unpack_string())
        dimensions = []
        shape = []
        dims = self._unpack_int()

        for i in range(dims):
            dimid = self._unpack_int()
            dimname = self._dims[dimid]
            dimensions.append(dimname)
            dim = self.dimensions[dimname]
            shape.append(dim)
        dimensions = tuple(dimensions)
        shape = tuple(shape)

        attributes = self._read_att_array()
        nc_type = self.fp.read(4)
        vsize = self._unpack_int()
        begin = [self._unpack_int, self._unpack_int64][self.version_byte-1]()

        typecode, size = TYPEMAP[nc_type]
        dtype_ = '>%s' % typecode

        return name, dimensions, shape, attributes, typecode, size, dtype_, begin, vsize

    def _read_values(self):
        nc_type = self.fp.read(4)
        n = self._unpack_int()

        typecode, size = TYPEMAP[nc_type]

        count = n*size
        values = self.fp.read(int(count))
        self.fp.read(-count % 4)  # read padding

        if typecode is not 'c':
            values = fromstring(values, dtype='>%s' % typecode)
            if values.shape == (1,): values = values[0]
        else:
            values = values.rstrip(asbytes('\x00'))
        return values

    def _pack_begin(self, begin):
        if self.version_byte == 1:
            self._pack_int(begin)
        elif self.version_byte == 2:
            self._pack_int64(begin)

    def _pack_int(self, value):
        self.fp.write(array(value, '>i').tostring())
    _pack_int32 = _pack_int

    def _unpack_int(self):
        return int(fromstring(self.fp.read(4), '>i')[0])
    _unpack_int32 = _unpack_int

    def _pack_int64(self, value):
        self.fp.write(array(value, '>q').tostring())

    def _unpack_int64(self):
        return fromstring(self.fp.read(8), '>q')[0]

    def _pack_string(self, s):
        count = len(s)
        self._pack_int(count)
        self.fp.write(asbytes(s))
        self.fp.write(asbytes('0') * (-count % 4))  # pad

    def _unpack_string(self):
        count = self._unpack_int()
        s = self.fp.read(count).rstrip(asbytes('\x00'))
        self.fp.read(-count % 4)  # read padding
        return s


class netcdf_variable(object):
    """
    A data object for the `netcdf` module.

    `netcdf_variable` objects are constructed by calling the method
    `netcdf_file.createVariable` on the `netcdf_file` object. `netcdf_variable`
    objects behave much like array objects defined in numpy, except that their
    data resides in a file. Data is read by indexing and written by assigning
    to an indexed subset; the entire array can be accessed by the index ``[:]``
    or (for scalars) by using the methods `getValue` and `assignValue`.
    `netcdf_variable` objects also have attribute `shape` with the same meaning
    as for arrays, but the shape cannot be modified. There is another read-only
    attribute `dimensions`, whose value is the tuple of dimension names.

    All other attributes correspond to variable attributes defined in
    the NetCDF file. Variable attributes are created by assigning to an
    attribute of the `netcdf_variable` object.

    Parameters
    ----------
    data : array_like
        The data array that holds the values for the variable.
        Typically, this is initialized as empty, but with the proper shape.
    typecode : dtype character code
        Desired data-type for the data array.
    size : int
        Desired element size for the data array.
    shape : sequence of ints
        The shape of the array.  This should match the lengths of the
        variable's dimensions.
    dimensions : sequence of strings
        The names of the dimensions used by the variable.  Must be in the
        same order of the dimension lengths given by `shape`.
    attributes : dict, optional
        Attribute values (any type) keyed by string names.  These attributes
        become attributes for the netcdf_variable object.


    Attributes
    ----------
    dimensions : list of str
        List of names of dimensions used by the variable object.
    isrec, shape
        Properties

    See also
    --------
    isrec, shape

    """
    def __init__(self, data, typecode, size, shape, dimensions, attributes=None):
        self.data = data
        self._typecode = typecode
        self._size = size
        self._shape = shape
        self.dimensions = dimensions

        self._attributes = attributes or {}
        for k, v in self._attributes.items():
            self.__dict__[k] = v

    def __setattr__(self, attr, value):
        # Store user defined attributes in a separate dict,
        # so we can save them to file later.
        try:
            self._attributes[attr] = value
        except AttributeError:
            pass
        self.__dict__[attr] = value

    def isrec(self):
        """Returns whether the variable has a record dimension or not.

        A record dimension is a dimension along which additional data could be
        easily appended in the netcdf data structure without much rewriting of
        the data file. This attribute is a read-only property of the
        `netcdf_variable`.

        """
        return self.data.shape and not self._shape[0]
    isrec = property(isrec)

    def shape(self):
        """Returns the shape tuple of the data variable.

        This is a read-only attribute and can not be modified in the
        same manner of other numpy arrays.
        """
        return self.data.shape
    shape = property(shape)

    def getValue(self):
        """
        Retrieve a scalar value from a `netcdf_variable` of length one.

        Raises
        ------
        ValueError
            If the netcdf variable is an array of length greater than one,
            this exception will be raised.

        """
        return self.data.item()

    def assignValue(self, value):
        """
        Assign a scalar value to a `netcdf_variable` of length one.

        Parameters
        ----------
        value : scalar
            Scalar value (of compatible type) to assign to a length-one netcdf
            variable. This value will be written to file.

        Raises
        ------
        ValueError
            If the input is not a scalar, or if the destination is not a length-one
            netcdf variable.

        """
        if not self.data.flags.writeable:
            # Work-around for a bug in NumPy.  Calling itemset() on a read-only
            # memory-mapped array causes a seg. fault.
            # See NumPy ticket #1622, and SciPy ticket #1202.
            # This check for `writeable` can be removed when the oldest version
            # of numpy still supported by scipy contains the fix for #1622.
            raise RuntimeError("variable is not writeable")

        self.data.itemset(value)

    def typecode(self):
        """
        Return the typecode of the variable.

        Returns
        -------
        typecode : char
            The character typecode of the variable (eg, 'i' for int).

        """
        return self._typecode

    def itemsize(self):
        """
        Return the itemsize of the variable.

        Returns
        -------
        itemsize : int
            The element size of the variable (eg, 8 for float64).

        """
        return self._size

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, data):
        # Expand data for record vars?
        if self.isrec:
            if isinstance(index, tuple):
                rec_index = index[0]
            else:
                rec_index = index
            if isinstance(rec_index, slice):
                recs = (rec_index.start or 0) + len(data)
            else:
                recs = rec_index + 1
            if recs > len(self.data):
                shape = (recs,) + self._shape[1:]
                self.data.resize(shape)
        self.data[index] = data


NetCDFFile = netcdf_file
NetCDFVariable = netcdf_variable

class Genesis(object):

    def __init__(self, runid, d=None):
        """Instantiate the Genesis object

        Parameters
        ----------
        runid : int
            Runid (usually file basename)

        Notes
        -----
        The Genesis class is an interface to the Exodus II api. Its methods
        are named after the analogous method from the Exodus II C bindings,
        minus the prefix 'ex_'.

        """
        d = d or os.getcwd()
        filepath = os.path.join(d, runid + ".exo")
        self.db = self.open_db(filepath, mode="w")

        version = 5.0300002
        setattr(self.db, ATT_API_VERSION, version)
        setattr(self.db, ATT_VERSION, version)
        setattr(self.db, ATT_FLT_WORDSIZE, 4)
        setattr(self.db, ATT_FILESIZE, 1)

        setattr(self.db, ATT_FILENAME, os.path.basename(filepath))
        setattr(self.db, ATT_RUNID, runid)

        # standard ExodusII dimensioning
        self.db.createDimension(DIM_STR, MAX_STR_LENGTH + 1)
        self.db.createDimension(DIM_LIN, MAX_LINE_LENGTH + 1)
        self.db.createDimension(DIM_N4, 4)

        # initialize internal variables
        # internal counters
        self.counter = {PX_ELEM_BLK: 0, PX_NODE_SET: 0, PX_SIDE_SET: 0}
        self.objids = {PX_ELEM_BLK: {}, PX_NODE_SET: {}, PX_SIDE_SET: {}}
        pass

    def open_db(self, filepath, mode="r"):
        """Open the netcdf database file"""
        if mode not in "rw":
            raise ExodusIIFileError("{0}: bad read/write mode".format(mode))
        return netcdf_file(filepath, mode)

    def close(self):
        self.db.close()

    def update(self):
        pass

    def register_id(self, obj_type, obj_id, obj_idx):
        if obj_id in self.objids[obj_type]:
            raise ExodusIIFileError("{0}: duplicate {1} block  "
                                    "ID".format(elem_blk_id, obj_type))
        self.objids[obj_type][obj_id] = obj_idx

    def get_obj_idx(self, obj_type, obj_id):
        return self.objids[obj_type].get(obj_id)

    @property
    def filename(self):
        return self.db.filename

    # ---------------------------------------------------- GENESIS OUTPUT --- #
    def put_init(self, title, num_dim, num_nodes, num_elem, num_elem_blk,
                 num_node_sets, num_side_sets):
        """Writes the initialization parameters to the EXODUS II file

        Parameters
        ----------
        title : str
            Title

        num_dim : int
            Number of spatial dimensions [1, 2, 3]

        num_nodes : int
            Number of nodes

        num_elem : int
            Number of elements

        num_elem_blk : int
            Number of element blocks

        num_node_sets : int
            Number of node sets

        num_side_sets : int
            Number of side sets

        """
        self.db.title = title
        setattr(self.db, ATT_TITLE, title)

        # Create required dimensions
        self.db.createDimension(DIM_NUM_DIM, num_dim)
        self.db.createDimension(DIM_NUM_NODES, num_nodes)
        self.db.createDimension(DIM_NUM_ELEM, num_elem)

        def create_and_alloc(num, dim, var_id, var_stat, var_name, nz=0):
            if not num:
                return

            # block/set meta data
            self.db.createDimension(dim, num)

            if nz: prop1 = np.arange(num, dtype=np.int32)
            else: prop1 = np.zeros(num, dtype=np.int32)
            self.db.createVariable(var_id, DTYPE_INT, (dim,))
            self.db.variables[var_id][:] = prop1
            setattr(self.db.variables[var_id], ATT_PROP_NAME, "ID")

            if nz: status = np.ones(num, dtype=np.int32)
            else: status = np.zeros(num, dtype=np.int32)
            self.db.createVariable(var_stat, DTYPE_INT, (dim,))
            self.db.variables[var_stat][:] = status

            names = np.array([" " * MAX_STR_LENGTH for _ in prop1])
            self.db.createVariable(var_name, DTYPE_TXT, (dim, DIM_STR))
            for (i, name) in enumerate(names):
                self.db.variables[var_name][i][:] = name

        # element block meta data
        num_elem_blk = max(num_elem_blk, 1)
        create_and_alloc(num_elem_blk, DIM_NUM_EL_BLK, VAR_ID_EL_BLK,
                         VAR_STAT_EL_BLK, VAR_NAME_EL_BLK, nz=1)

        # node set meta data
        create_and_alloc(num_node_sets, DIM_NUM_NS, VAR_NS_IDS,
                         VAR_NS_STAT, VAR_NAME_NS)

        # side set meta data
        create_and_alloc(num_side_sets, DIM_NUM_SS, VAR_SS_IDS,
                         VAR_SS_STAT, VAR_NAME_SS)

        # set defaults
        self.db.createVariable(VAR_NAME_COOR, DTYPE_TXT, (DIM_NUM_DIM, DIM_STR))
        for i in range(num_dim):
            self.db.createVariable(PX_VAR_COORDS(i), DTYPE_FLT, (DIM_NUM_NODES,))

    def put_coord_names(self, coord_names):
        """Writes the names of the coordinate arrays to the database.

        Parameters
        ----------
        coord_names : array_like
            Array containing num_dim names (of length MAX_STR_LENGTH) of the
            nodal coordinate arrays.

        """
        num_dim = self.db.dimensions[DIM_NUM_DIM]
        for i in range(num_dim):
            self.db.variables[VAR_NAME_COOR][i][:] = coord_names[i]
        return

    def put_coord(self, *coords):
        """Write the names of the coordinate arrays

        Parameters
        ----------
        coords: x, y, z : each array_like
            x, y, z coordinates

        """
        num_dim = self.db.dimensions[DIM_NUM_DIM]
        for i in range(num_dim):
            self.db.variables[PX_VAR_COORDS(i)][:] = coords[i]

        return

    def put_map(self, elem_map):
        """Writes out the optional element order map to the database

        Parameters
        ----------
        elem_map : array_like
            The element map

        Notes
        -----
        The following code generates a default element order map and outputs
        it to an open EXODUS II file. This is a trivial case and included just
        for illustration. Since this map is optional, it should be written out
        only if it contains something other than the default map.

        elem_map = []
        for i in range(num_elem):
            elem_map.append(i+1)

        """
        num_elem = self.db.dimensions[DIM_NUM_ELEM]
        if len(elem_map) > num_elem:
            raise ExodusIIFileError("len(elem_map) > num_elem")
        self.db.createVariable(PX_VAR_EL_MAP, DTYPE_INT, (DIM_NUM_ELEM,))
        self.db.variables[PX_VAR_EL_MAP][:] = elem_map
        return

    def put_elem_num_map(self, elem_num_map):
        """Writes out the optional element order map to the database

        Parameters
        ----------
        elem_map : array_like
            The element map

        Notes
        -----
        The following code generates a default element order map and outputs
        it to an open EXODUS II file. This is a trivial case and included just
        for illustration. Since this map is optional, it should be written out
        only if it contains something other than the default map.

        elem_map = []
        for i in range(num_elem):
            elem_map.append(i+1)

        """
        num_elem = self.db.dimensions[DIM_NUM_ELEM]
        if len(elem_num_map) > num_elem:
            raise ExodusIIFileError("len(elem_map) > num_elem")
        self.db.createVariable(VAR_ELEM_MAP(1), DTYPE_INT, (DIM_NUM_ELEM,))
        self.db.variables[VAR_ELEM_MAP(1)][:] = elem_num_map
        return

    def put_elem_block(self, elem_blk_id, elem_type, num_elem_this_blk,
                       num_nodes_per_elem, num_attr):
        """Write parameters used to describe an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID.

        elem_type : str
            The type of elements in the element block. The maximum length of
            this string is MAX_STR_LENGTH. For historical reasons, this
            string should be all upper case.

        num_elem_this_blk : int
            The number of elements in the element block.

        num_nodes_per_elem : int
            Number of nodes per element in the element block

        num_attr : int
            The number of attributes per element in the element block.

        """
        num_elem_blk = self.db.dimensions[DIM_NUM_EL_BLK]
        if self.counter[PX_ELEM_BLK] == num_elem_blk:
            raise ExodusIIFileError("number element blocks exceeded")

        elem_blk_id = int(elem_blk_id)

        # dimensioning
        i = self.counter[PX_ELEM_BLK]
        self.db.createDimension(DIM_NUM_EL_IN_BLK(i+1), num_elem_this_blk)
        self.db.createDimension(DIM_NUM_NOD_PER_EL(i+1), num_nodes_per_elem)

        # store the element block ID
        self.db.variables[VAR_ID_EL_BLK][i] = elem_blk_id
        self.register_id(PX_ELEM_BLK, elem_blk_id, i)

        # set up the element block connectivity
        self.db.createVariable(VAR_CONN(i+1), DTYPE_INT,
                               (DIM_NUM_EL_IN_BLK(i+1), DIM_NUM_NOD_PER_EL(i+1)))
        setattr(self.db.variables[VAR_CONN(i+1)], "elem_type", elem_type.upper())
        conn = np.zeros((num_elem_this_blk, num_nodes_per_elem))
        self.db.variables[VAR_CONN(i+1)][:] = conn

        # element block attributes
        if num_attr:
            self.db.createDimension(DIM_NUM_ATT_IN_BLK(i+1), num_attr)

            self.db.createVariable(VAR_ATTRIB(i+1), DTYPE_FLT,
                               (DIM_NUM_EL_IN_BLK(i+1), DIM_NUM_ATT_IN_BLK(i+1)))
            self.db.variables[VAR_ATTRIB(i+1)][:] = np.zeros(num_attr)

            self.db.createVariable(VAR_NAME_ATTRIB(i+1), DTYPE_TXT,
                                   (DIM_NUM_ATT_IN_BLK(i+1), DIM_STR))
            self.db.variables[VAR_NAME_ATTRIB(i+1)][:] = " " * MAX_STR_LENGTH

        # increment block number
        self.counter[PX_ELEM_BLK] += 1
        return

    def put_prop_names(self, obj_type, num_props, prop_names, o=0, nofill=0):
        """Writes property names and allocates space for property arrays used
        to assign integer properties to element blocks, node sets, or side
        sets.

        Parameters
        ----------
        obj_type : int

        num_props : int
            The number of properties

        prop_names : array_like
            Array containing num_props names

        """
        name, dim = PX_PROPINFO(obj_type)
        n = self.db.dimensions[dim]
        for i in range(num_props):
            I = o + i + 2
            self.db.createVariable(name(I), DTYPE_INT, (dim,))
            setattr(self.db.variables[name(I)], ATT_PROP_NAME, str(prop_names[i]))
            if not nofill:
                setattr(self.db.variables[name(I)], "_FillValue", 0)
            # _FillValue not yet implemented
            self.db.variables[name(I)][:] = np.zeros(n, dtype=np.int32)
        return I

    def put_prop(self, obj_type, obj_id, prop_name, value):
        """Stores an integer property value to a single element block, node
        set, or side set.

        Parameters
        ----------
        obj_type : int
            The type of object

        obj_id : int
            The element block, node set, or side set ID

        prop_name : str
            Property name

        value : int

        """
        name, dim = PX_PROPINFO(obj_type)
        n = len([x for x in self.db.variables if name("") in x and x != name(1)])
        ids = self.db.variables[name(1)].data
        idx = np.where(ids == obj_id)[0][0]
        i = 0
        for i in range(n):
            var = self.db.variables[name(i+2)]
            if var.name == prop_name:
                var[idx] = value
                break
        else:
            # register the variable and assign its value
            idx = np.where(ids == obj_id)[0][0]
            I = self.put_prop_names(obj_type, 1, [prop_name], o=n)
            self.db.variables[name(I)][idx] = value

    def put_prop_array(self, obj_type, prop_name, values):
        """Stores an array of (num_elem_blk, num_node_sets, or num_side_sets)
        integer property values for all element blocks, node sets, or side
        sets.

        Parametes
        ---------
        obj_type : int
            The type of object; use on of the following options
            EX_ELEM_BLOCK
            EX_NODE_SET
            EX_SIDE_SET

        prop_name : string
            Property name

        values : array_like
            An array of property values

        """
        name, dim = PX_PROPINFO(obj_type)
        n = len([x for x in self.db.variables if name("") in x and x != name(1)])
        for i in range(n):
            var = self.db.variables[name(i+2)]
            if var.name == prop_name:
                var[:] = values
                break
        else:
            # register the variable and assign its value
            I = self.put_prop_names(obj_type, 1, [prop_name], o=n, nofill=1)
            self.db.variables[name(I)][:] = values
        return

    def put_elem_conn(self, elem_blk_id, blk_conn):
        """writes the connectivity array for an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        connect : array_like
            Connectivity array, list of nodes that define each element in the
            block

        """
        name, dim = PX_PROPINFO(EX_ELEM_BLOCK)
        i = self.get_obj_idx(PX_ELEM_BLK, elem_blk_id)
        if i is None:
            raise ExodusIIFileError("{0}: element ID not valid".format(elem_blk_id))

        # dimensions
        dim_e = DIM_NUM_EL_IN_BLK(i+1)
        num_elem_this_blk = self.db.dimensions[dim_e]

        dim_n = DIM_NUM_NOD_PER_EL(i+1)
        num_node_this_elem = self.db.dimensions[dim_n]

        netb, nnte = blk_conn.shape
        if netb != num_elem_this_blk:
            raise ExodusIIFileError(
                "expected {0} elements in element block {1}, "
                "got {2}".format(num_elem_this_blk, elem_blk_id, netb))

        if nnte != num_node_this_elem:
            raise ExodusIIFileError(
                "expected {0} nodes in element block {1}, "
                "got {2}".format(num_node_this_elem, elem_blk_id, nnte))

        # connectivity
        self.db.variables[VAR_CONN(i+1)][:] = blk_conn + PX_OFFSET
        return

    def put_elem_attr(self, elem_blk_id, attr):
        """writes the attribute to the

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        attr : array_like, (num_elem_this_block, num_attr)
            List of attributes for the element block

        """
        name, dim = PX_PROPINFO(EX_ELEM_BLOCK)
        i = self.get_obj_idx(PX_ELEM_BLK, elem_blk_id)
        if i is None:
            raise ExodusIIFileError("{0}: invalid element block "
                                    "ID".format(elem_blk_id))

        # dimensions
        dim_e = DIM_NUM_EL_IN_BLK(i+1)
        num_elem_this_blk = self.db.dimensions[dim_e]

        dim_a = DIM_NUM_ATT_IN_BLK(i+1)
        num_attr_this_block = self.db.dimensions[dim_a]

        # put the attribute
        self.db.variables[VAR_ATTRIB(i+1)][:] = attr
        return

    def put_node_set_param(self, node_set_id, num_nodes_in_set,
                           num_dist_fact_in_set=0):
        """Writes the node set ID, the number of nodes which describe a single
        node set, and the number of distribution factors for the node set.

        Parameters
        ----------
        node_set_id : int
            The node set ID

        num_nodes_in_set : int
            Number of nodes in set

        num_dist_fact_in_set : int
            The number of distribution factors in the node set. This should be
            either 0 (zero) for no factors, or should equal num_nodes_in_set.

        """
        num_node_sets = self.db.dimensions[DIM_NUM_NS]
        if self.counter[PX_NODE_SET] == num_node_sets:
            raise ExodusIIFileError("number of node sets exceeded")

        i = self.counter[PX_NODE_SET]
        self.register_id(PX_NODE_SET, node_set_id, i)

        # store node set ID
        self.db.variables[VAR_NS_IDS][i] = int(node_set_id)

        self.db.createDimension(DIM_NUM_NOD_NS(i+1), num_nodes_in_set)
        self.db.createVariable(VAR_NODE_NS(i+1), DTYPE_INT,
                               (DIM_NUM_NOD_NS(i+1),))

        if num_dist_fact_in_set:
            self.db.createDimension(DIM_NUM_DF_NS(i+1), num_dist_fact_in_set)
            self.db.createVariable(VAR_FACT_NS(i+1), DTYPE_FLT,
                                   (DIM_NUM_NOD_NS(i+1),))

        self.db.variables[VAR_NS_STAT][i] = 1

        self.counter[PX_NODE_SET] += 1

    def put_node_set(self, node_set_id, node_set_node_list):
        """Writes the node list for a single node set.

        Parameters
        ----------
        node_ set_id : int
            The node set ID.

        node_set_node_list : array_like
            Array containing the node list for the node set. Internal node IDs
            are used in this list.

        Notes
        -----
        The function put_node_set_param must be called before this routine is
        invoked.

        """
        node_set_id = int(node_set_id)
        i = self.get_obj_idx(PX_NODE_SET, node_set_id)
        if i is None:
            raise ExodusIIFileError("bad node set ID")
        nodes = node_set_node_list + PX_OFFSET
        self.db.variables[VAR_NODE_NS(i+1)][:] = nodes
        return

    def put_node_set_dist_fact(self, node_set_id, node_set_dist_fact):
        """Writes distribution factors for a single node set

        Parameters
        ----------
        node_ set_id : int
            The node set ID.

        node_set_dist_fact : array_like
            Array containing the distribution factors for each node in the set

        Notes
        -----
        The function put_node_set_param must be called before this routine is
        invoked.

        """
        node_set_id = int(node_set_id)
        i = self.get_obj_idx(PX_NODE_SET, node_set_id)
        if i is None:
            raise ExodusIIFileError("bad node set ID")
        dim = self.db.dimensions[DIM_NUM_DF_NS(i+1)]
        if len(node_set_dist_fact) != dim:
            raise ExodusIIFileError("len(node_set_dist_fact) incorrect")
        self.db.variables[VAR_FACT_NS(i+1)][:] = node_set_dist_fact

    def put_side_set_param(self, side_set_id, num_sides_in_set,
                           num_dist_fact_in_set=0):
        """Writes the side set ID, the number of sides (faces on 3-d element,
        edges on 2-d) which describe a single side set, and the number of
        distribution factors on the side set.

        Parameters
        ----------
        side_set_id : int
            The side set ID

        num_sides_in_set : int
            Number of sides in set

        num_dist_fact_in_set : int
            The number of distribution factors in the side set. This should be
            either 0 (zero) for no factors, or should equal num_sides_in_set.

        """
        num_side_sets = self.db.dimensions[DIM_NUM_SS]
        if self.counter[PX_SIDE_SET] == num_side_sets:
            raise ExodusIIFileError("number of side sets exceeded")

        i = self.counter[PX_SIDE_SET]
        self.register_id(PX_SIDE_SET, side_set_id, i)

        # store side set ID
        self.db.variables[VAR_SS_IDS][i] = int(side_set_id)

        self.db.createDimension(DIM_NUM_SIDE_SS(i+1), num_sides_in_set)
        self.db.createVariable(VAR_SIDE_SS(i+1), DTYPE_INT, (DIM_NUM_SIDE_SS(i+1),))
        self.db.createVariable(VAR_ELEM_SS(i+1), DTYPE_INT, (DIM_NUM_SIDE_SS(i+1),))

        if num_dist_fact_in_set:
            self.db.createDimension(DIM_NUM_DF_SS(i+1), num_dist_fact_in_set)
            self.db.createVariable(VAR_FACT_SS(i+1), DTYPE_FLT,
                                   (DIM_NUM_DF_SS(i+1),))

        self.db.variables[VAR_SS_STAT][i] = 1

        self.counter[PX_SIDE_SET] += 1

    def put_side_set(self, side_set_id, side_set_elem_list,
                     side_set_side_list):
        """Writes the side set element list and side set side (face on 3-d
        element types; edge on 2-d element types) list for a single side set.

        Parameters
        ----------
        side_ set_id : int
            The side set ID.

        side_set_elem_list : array_like
            Array containing the elements in the side set. Internal element
            IDs are used in this list

        side_set_side_list : array_like
            Array containing the side in the side set

        Notes
        -----
        The function put_side_set_param must be called before this routine is
        invoked.

        """
        side_set_id = int(side_set_id)
        i = self.get_obj_idx(PX_SIDE_SET, side_set_id)
        if i is None:
            raise ExodusIIFileError("bad side set ID")

        sides = side_set_side_list + PX_OFFSET
        elems = side_set_elem_list + PX_OFFSET
        self.db.variables[VAR_SIDE_SS(i+1)][:] = sides
        self.db.variables[VAR_ELEM_SS(i+1)][:] = elems
        return

    def put_side_set_dist_fact(self, side_set_id, side_set_dist_fact):
        """Writes distribution factors for a single side set

        Parameters
        ----------
        side_ set_id : int
            The side set ID.

        side_set_dist_fact : array_like
            Array containing the distribution factors for each side in the set

        Notes
        -----
        The function put_side_set_param must be called before this routine is
        invoked.

        """
        side_set_id = int(side_set_id)
        i = self.get_obj_idx(PX_SIDE_SET, side_set_id)
        if i is None:
            raise ExodusIIFileError("bad side set ID")
        dim = self.db.dimensions[DIM_NUM_DF_SS(i+1)]
        if len(side_set_dist_fact) != dim:
            raise ExodusIIFileError("len(side_set_dist_fact) incorrect")
        self.db.variables[VAR_FACT_SS(i+1)][:] = side_set_dist_fact

    def put_qa(self, num_qa_records, qa_records):
        """Writes the QA records to the database.

        Parameters
        ----------
        num_qa_records : int
            Then number of QA records

        qa_record : array_like, (num_qa_records, 4)
            Array containing the QA records

        Notes
        -----
        Each QA record contains for MAX_STR_LENGTH-byte character strings. The
        character strings are

          1) the analysis code name
          2) the analysis code QA descriptor
          3) the analysis date
          4) the analysis time

        """
        self.db.createDimension(DIM_NUM_QA, num_qa_records)
        self.db.createVariable(VAR_QA_TITLE, DTYPE_TXT,
                               (DIM_NUM_QA, DIM_N4, DIM_STR))
        for (i, qa_record) in enumerate(qa_records):
            self.db.variables[VAR_QA_TITLE][i, 0, :] = qa_record[0]
            self.db.variables[VAR_QA_TITLE][i, 1, :] = qa_record[1]
            self.db.variables[VAR_QA_TITLE][i, 2, :] = qa_record[2]
            self.db.variables[VAR_QA_TITLE][i, 3, :] = qa_record[3]
        return

    def put_info(self, num_info, info):
        """Writes information records to the database. The records are
        MAX_LINE_LENGTH-character strings.

        Parameters
        ----------
        info : array_like, (num_info, )
            Array containing the information records

        """
        """Reads/writes information records to the database"""
        num_info = len(info)
        self.db.createDimension(DIM_NUM_INFO, num_info)
        self.db.createVariable(VAR_INFO, DTYPE_TXT, (DIM_NUM_INFO, DIM_LIN))
        for (i, info_record) in enumerate(info):
            self.db.variables[VAR_INFO][i] = info_record
        return


class NotYetImplemented(Exception):
    def __init__(self, meth):
        self.message = "{0}: ExodusIIFile method not yet implemented".format(meth)
        super(NotYetImplemented, self).__init__(self.message)


class ExodusIIReader(object):
    """Exodus output databse reader

    """
    def __init__(self, filepath):
        self.db = self.open_db(filepath)
        self.set_id_idx_map = self._get_set_ids()
        self.var_id_idx_map = self._get_var_ids()
        pass

    def __repr__(self):
        return self.summary()

    def open_db(self, filepath):
        """Open the netcdf database file"""
        return netcdf_file(filepath, "r")

    def close(self):
        self.db.close()

    def update(self):
        pass

    @property
    def filename(self):
        return getattr(self.db, ATT_FILENAME)

    @property
    def title(self):
        return getattr(self.db, ATT_TITLE)

    @property
    def num_dim(self):
        return self.db.dimensions[DIM_NUM_DIM]

    @property
    def num_nodes(self):
        return self.db.dimensions[DIM_NUM_NODES]

    @property
    def num_elem(self):
        return self.db.dimensions[DIM_NUM_ELEM]

    @property
    def num_elem_blk(self):
        return self.db.dimensions[DIM_NUM_EL_BLK]

    @property
    def num_node_sets(self):
        return self.db.dimensions.get(DIM_NUM_NS, 0)

    @property
    def num_side_sets(self):
        return self.db.dimensions.get(DIM_NUM_SS, 0)

    @property
    def glob_var_names(self):
        return chara_to_text(self.db.variables[VAR_NAME_GLO_VAR].data, aslist=True)

    @property
    def elem_var_names(self):
        return chara_to_text(self.db.variables[VAR_NAME_ELE_VAR].data, aslist=True)

    @property
    def node_var_names(self):
        return chara_to_text(self.db.variables[VAR_NAME_NOD_VAR].data, aslist=True)

    @property
    def coord_names(self):
        return self.get_coord_names()

    @property
    def coords(self):
        return self.get_coord()

    @property
    def num_time_steps(self):
        return self.db.variables[VAR_WHOLE_TIME].shape[0]

    @property
    def elem_blk_ids(self):
        return self.db.variables[VAR_ID_EL_BLK].data

    @property
    def node_set_ids(self):
        try: return self.db.variables[VAR_NS_IDS].data
        except KeyError: return []

    @property
    def side_set_ids(self):
        try: return self.db.variables[VAR_SS_IDS].data
        except KeyError: return []

    @property
    def elem_num_map(self):
        return self.get_elem_num_map()

    @property
    def connect(self):
        return self.get_db_conn()

    def setidx(self, obj_type, obj_id):
        return self.set_id_idx_map[obj_type].get(obj_id)

    def varidx(self, var_typ, var_name):
        return self.var_id_idx_map[var_typ].get(var_name)

    def _get_set_ids(self):
        set_id_idx_map = {}
        set_id_idx_map[PX_ELEM_BLK] = dict((j, i)
                                   for (i, j) in enumerate(self.elem_blk_ids))
        set_id_idx_map[PX_NODE_SET] = dict((j, i)
                                   for (i, j) in enumerate(self.node_set_ids))
        set_id_idx_map[PX_SIDE_SET] = dict((j, i)
                                   for (i, j) in enumerate(self.side_set_ids))
        return set_id_idx_map

    def _get_var_ids(self):
        var_id_idx_map = {}
        var_id_idx_map[PX_VAR_ELE] = dict((j, i)
                                  for (i, j) in enumerate(self.elem_var_names))
        var_id_idx_map[PX_VAR_NOD] = dict((j, i)
                                  for (i, j) in enumerate(self.node_var_names))
        var_id_idx_map[PX_VAR_GLO] = dict((j, i)
                                  for (i, j) in enumerate(self.glob_var_names))
        return var_id_idx_map

    def get_init(self):
        """Gets the initialization parameters from the ExodusII file

        Parameters
        ----------
        exoid : int
            File ID as returned by one of the factory initialization methods

        Returns
        -------
        title : str
            Title

        num_dim : int
            Number of spatial dimensions [1, 2, 3]

        num_nodes : int
            Number of nodes

        num_elem : int
            Number of elements

        num_elem_blk : int
            Number of element blocks

        num_node_sets : int
            Number of node sets

        num_side_sets : int
            Number of side sets

        """
        return (self.title, self.num_dim, self.num_nodes, self.num_elem,
                self.num_elem_blk, self.num_node_sets, self.num_side_sets)

    def get_all_times(self):
        """reads the time value for all times

        Parameters
        ----------

        Returns
        -------
        times : ndarray of floats
            Times for all steps

        """
        return self.db.variables[VAR_WHOLE_TIME].data[:]

    def get_time(self, step):
        """reads the time value for a specified time step

        Parameters
        ----------
        step : int
            Time step, 0 based indexing

        Returns
        -------
        time : float
            Time at time step

        """
        return self.db.variables[VAR_WHOLE_TIME].data[step]

    def get_coord_names(self):
        """Reads the names of the coordinate arrays from the database.

        Returns
        -------
        coord_names : array_like
            Array containing num_dim names (of length MAX_STR_LENGTH) of the
            nodal coordinate arrays.

        """
        return chara_to_text(self.db.variables[VAR_NAME_COOR].data[:])

    def get_coord(self, idx=None):
        """Read the coordinates of the nodes

        Returns
        -------
        x, y, z : array_like
            x, y, z coordinates

        """
        if idx is not None:
            return self.db.variables[VAR_COORDS(idx)].data[:]

        coords = []
        for i in range(self.num_dim):
            coords.append(self.db.variables[VAR_COORDS(i)].data[:])
        return coords

    def get_elem_block(self, elem_blk_id):
        """Returns parameters used to describe an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID.

        Returns
        -------
        elem_type : str
            The type of elements in the element block.

        num_elem_this_blk : int
            The number of elements in the element block.

        num_nodes_per_elem : int
            Number of nodes per element in the element block

        num_attr : int
            The number of attributes per element in the element block.

        """
        i = self.setidx(PX_ELEM_BLK, elem_blk_id)
        if i is None:
            raise ExodusIIFileError("{0}: not a valid element block "
                                    "ID".format(elem_blk_id))
        elem_type = self.db.variables[VAR_CONN(i+1)].elem_type
        num_elem_this_blk = self.db.dimensions[DIM_NUM_EL_IN_BLK(i+1)]
        num_nodes_per_elem = self.db.dimensions[DIM_NUM_NOD_PER_EL(i+1)]
        num_attr = self.db.dimensions[DIM_NUM_ATT_IN_BLK(i+1)]
        return elem_type, num_elem_this_blk, num_nodes_per_elem, num_attr

    def get_elem_conn(self, elem_blk_id, disp=0):
        """reads the connectivity array for an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        Returns
        -------
        connect : ndarray, (num_elem_this_blk, num_nodes_per_elem)
            Connectivity array; a list of nodes (internal node IDs; see Node
            Number Map) that define each element. The element index cycles faster
            than the node index.

        """
        i = self.setidx(PX_ELEM_BLK, elem_blk_id)
        if i is None:
            raise ExodusIIFileError("{0}: not a valid element block "
                                    "ID".format(elem_blk_id))
        var = self.db.variables[VAR_CONN(i+1)]
        if not disp:
            return var.data
        return {"connect": var.data, "elem_type": var.elem_type}

    def get_db_conn(self):
        """Reads the connectivity array for all element blocks from the database

        Returns
        -------
        connect : ndarray, (num_elem_this_blk, num_nodes_per_elem)
            Connectivity array; a list of nodes (internal node IDs; see Node
            Number Map) that define each element. The element index cycles faster
            than the node index.

        """
        connect = []
        for (i, elem_blk_id) in enumerate(self.elem_blk_ids):
            conn = self.get_elem_conn(elem_blk_id)
            connect.append(conn)
        return connect

    def get_elem_num_map(self):
        """Returns the element map attribute

        Returns
        -------
        elem_num_map : array_like
            The element number map

        """
        try:
            return self.db.variables[VAR_ELEM_MAP(1)].data[:]
        except KeyError:
            return

    def get_map(self):
        """Returns the optimized element order map attribute

        Returns
        -------
        elem_map : array_like
            The element order map

        """
        try:
            return self.db.variables[PX_VAR_EL_MAP].data[:]
        except KeyError:
            return

    def get_info(self):
        """Reads information records from the database. The records are
        MAX_LINE_LENGTH-character strings. Memory must be allocated for the
        information records before this call is made. The number of records
        can be determined by invoking inquire

        Returns
        -------
        info : array of strings
            information stored to exodus database

        """
        try:
            info = self.db.variables[VAR_INFO].data[:]
        except KeyError:
            return
        return self.chara_to_text(info)

    def get_glob_vars(self, step, disp=0):
        """Read all global variables at one time step

        Parameters
        ----------
        step : int
            Time step, 1 based indexing, it is changed here to 0 based

        disp : int, optional
            If disp > 0, return dictionary of {glob_var: glob_var_val}

        Returns
        -------
        var_values : ndarray, (num_glob_vars,)
            Global variable values for the stepth time step

        """
        try:
            data = self.db.variables[VAR_GLO_VAR].data[step]
        except IndexError:
            raise ExodusIIFileError("Error getting global variables at "
                                    "step {0}".format(step))
        if not disp:
            return data

        return dict(zip(self.glob_var_names, data))

    def get_glob_var_time(self, glob_var):
        """Read global variable through time

        glob_var : str
            The desired global variable

        Returns
        -------
        var_values : ndarray
            Array of the global variable

        """
        i = self.varidx(PX_VAR_GLO, glob_var)
        if i is None:
            raise ExodusIIFileError("{0}: global var not found".format(glob_var))
        return self.db.variables[VAR_GLO_VAR].data[:, i]

    def get_nodal_var(self, step, nodal_var):
        """Read nodal variable at one time step

        Parameters
        ----------
        step : int
            The time step, 0 indexing

        nodal_var : str
            The nodal variable

        Returns
        -------
        var_values : ndarray
            num_nodes values of the nodal_var_indexth nodal variable for the
            stepth time step.

        """
        if step == 0: step = 1
        i = self.varidx(PX_VAR_NOD, nodal_var)
        if i is None:
            raise ExodusIIFileError("{0}: nodal var not found".format(nodal_var))
        return self.db.variables[VAR_NOD_VAR_NEW(i+1)].data[step]

    def get_nodal_var_time(self, nodal_var, node_num):
        """Reads the values of a nodal variable for a single node through a
        specified number of time steps

        Parameters
        ----------
        nodal_var : str
            The desired nodal variable

        node_num : int
            The internal ID (see Node Number Map) of the desired node

        Returns
        -------
        var_vals : ndarray
            Array of (end_time_step - beg_time_step + 1) values of the
            node_numberth node for the nodal_var_indexth nodal variable.

        """
        i = self.varidx(PX_VAR_NOD, nodal_var)
        if i is None:
            raise ExodusIIFileError("{0}: nodal var not found".format(nodal_var))
        return self.db.variables[VAR_NOD_VAR_NEW(i+1)].data[:, node_num-PX_OFFSET]

    def get_elem_var(self, step, elem_var):
        """Read element variable at one time step

        Parameters
        ----------
        step : int
            The time step, 0 indexing

        elem_var : str
            The element variable

        Returns
        -------
        elem_var : ndarray

        """
        i = self.varidx(PX_VAR_ELE, elem_var)
        if i is None:
            raise ExodusIIFileError("{0}: elem var not found".format(elem_var))
        elem_var = []
        for (elem_blk_id, j) in self.set_id_idx_map[PX_ELEM_BLK].items():
            n = self.db.dimensions[DIM_NUM_EL_IN_BLK(j+1)]
            name = VAR_ELEM_VAR(i+1, j+1)
            elem_var.append(self.db.variables[name][step, :n])
        return np.array(elem_var)

    def get_elem_var_time(self, elem_var, elem_num, elem_blk_id=None):
        """Read element variable through time

        Parameters
        ----------
        elem_var : str
            The desired element variable

        elem_num : int
            The internal ID (see Element Number Map) of the desired element

        Returns
        -------
        var_vals : ndarray
            Array of (end_time_step - beg_time_step + 1) values of the
            node_numberth node for the nodal_var_indexth nodal variable.

        """
        i = self.varidx(PX_VAR_ELE, elem_var)
        if i is None:
            raise ExodusIIFileError("{0}: elem var not found".format(elem_var))

        if elem_blk_id is None:
            # find element block number that has this element assume that
            # elements are numbered contiguously with element block
            num_els = [self.db.dimensions[DIM_NUM_EL_IN_BLK(j+1)]
                       for j in range(self.num_elem_blk)]
            n = 0
            for (j, num_el) in enumerate(num_els):
                n += num_el
                if elem_num < n + PX_OFFSET:
                    break
            # j is now the element block id, now find the element number
            # relative the element block
            e = elem_num - sum(num_els[:j])
        else:
            j = self.setidx(PX_ELEM_BLK, elem_blk_id)
            if j is None:
                raise ExodusIIFileError("{0}: invalid element "
                                        "block".format(elem_blk_id))
            e = elem_num

        name = VAR_ELEM_VAR(i+1, j+1)
        return self.db.variables[name].data[:, e-PX_OFFSET]

    def summary(self):
        """return a summary string

        """
        S = ["Summary", "=" * 80]
        S.append("Exodus file name: {0}".format(self.filename))
        S.append("Title: {0}".format(self.title))
        S.append("Number of dimensions: {0}".format(self.num_dim))
        S.append("Coordinate names: {0}".format(" ".join(self.coord_names)))

        S.append("Number of nodes: {0}".format(self.num_nodes))
        S.append("Number of node sets: {0}, Ids={1}".format(
                self.num_node_sets,
                " ".join("{0}".format(x) for x in self.node_set_ids)))

        S.append("Number of elements: {0}".format(self.num_elem))
        S.append("Number of element blocks: {0} Ids={1}".format(
                self.num_elem_blk,
                " ".join("{0}".format(x) for x in self.elem_blk_ids)))

        S.append("Number of side sets: {0}".format(self.num_side_sets))

        S.append("Global Variables: {0}".format(", ".join(self.glob_var_names)))
        S.append("Element Variables: {0}".format(", ".join(self.elem_var_names)))
        S.append("Nodal Variables: {0}".format(", ".join(self.node_var_names)))

        S.append("Number of time steps: {0}".format(self.num_time_steps))
        for i in range(self.num_time_steps):
            S.append("    {0} {1}".format(i, self.get_time(i)))

        return "\n".join(S)

    # -------------- TJF: below methods need updating to PYTHON API
    def nodes_in_node_set(self, node_set_id):
        """Return a list of nodes in the node set

        Parameters
        ----------
        node_set_id : int
            The node set ID

        Returns
        -------
        node_list : ndarray
            Array of node IDs

        """
        raise NotYetImplemented("nodes_in_node_set")
        # Get only those nodes in the requested IDs
        node_set_params = self.node_set_params.get(node_set_id)
        if node_set_params is None:
            valid = ", ".join(["{0}".format(x)
                               for x in self.node_set_params])
            raise ExodusReaderError("{0}: invalid node set ID.  Valid IDs "
                                    "are: {1}".format(node_set_id, valid))
        return np.array(node_set_params["NODE LIST"])

    def nodes_in_region(self, xlims=(-PX_HUGE, PX_HUGE), ylims=(-PX_HUGE, PX_HUGE),
                        zlims=(-PX_HUGE, PX_HUGE), node_set_ids=None):
        """Return a list of nodes in the region bounded by (xlims, ylims, zlims)

        Parameters
        ----------
        xlims, ylims, zlims : tuple of floats
            Floats defining ([xyz]min, [xyz]max)

        node_set_id : list of ints, optional
            Node set IDs

        Returns
        -------
        node_list : ndarray
            Array of node IDs

        """
        raise NotYetImplemented("nodes_in_region")
        xmin, xmax = xlims
        ymin, ymax = ylims
        zmin, zmax = zlims
        if node_set_ids is None:
            node_list = np.arange(self.num_nodes)
        else:
            # Get only those nodes in the requested IDs
            if not isinstance(node_set_ids, (list, tuple)):
                node_set_ids = [node_set_ids]
            node_lists = [self.nodes_in_node_set(x) for x in node_set_ids]
            node_list = np.array([node for node_list in node_lists
                                  for node in node_list], dtype=np.int)
        return node_list[(self.XYZ[node_list, PY_X_COMP] >= xmin) &
                         (self.XYZ[node_list, PY_X_COMP] <= xmax) &
                         (self.XYZ[node_list, PY_Y_COMP] >= ymin) &
                         (self.XYZ[node_list, PY_Y_COMP] <= ymax) &
                         (self.XYZ[node_list, PY_Z_COMP] >= zmin) &
                         (self.XYZ[node_list, PY_Z_COMP] <= zmax)]

    def elems_in_region(self, xlims=(-PX_HUGE, PX_HUGE), ylims=(-PX_HUGE, PX_HUGE),
                        zlims=(-PX_HUGE, PX_HUGE), node_set_ids=None):
        """Return a list of elements in the region bounded by
        (xlims, ylims, zlims)

        Parameters
        ----------
        xlims, ylims, zlims : tuple of floats
            Floats defining ([xyz]min, [xyz]max)

        node_set_id : list of ints, optional
            Node set IDs

        Returns
        -------
        elem_list : ndarray
            Array of element IDs

        """
        raise NotYetImplemented("elems_in_region")
        # get the nodes in the bounding box
        node_list = self.nodes_in_region(xlims=xlims, ylims=ylims, zlims=zlims,
                                         node_set_ids=node_set_ids)
        # get elements connected to nodes
        return self.elems_from_nodes(node_list, strict=False)

    def elems_from_nodes(self, node_list, strict=True):
        """Return a list of elements whose nodes are in node_list

        Parameters
        ----------
        node_list : ndarray of ints
            Array of nodes

        strict : bool, optional
            If False, return element if more than half its nodes are in the
            node_list

        Returns
        -------
        elem_list : ndarray
            Array of element IDs

        """
        raise NotYetImplemented("elems_from_nodes")
        # loop through each element block, finding elements whose nodes are
        # in node_list.  Convert to global element IDs
        def issubset(a, b):
            """Return True if the set a is a subset of the set b, else False"""
            return a <= b if strict else len(a & b) >= len(a) / 2.

        elem_list, num_elems_seen, node_set = [], 0, set(node_list)
        for i, blk_conn in enumerate(self.connect):
            elem_list.extend([num_elems_seen + i_elem
                              for (i_elem, elem_conn) in enumerate(blk_conn)
                              if issubset(set(elem_conn), node_set)])
            num_elems_seen += blk_conn.shape[0]
        return np.array(elem_list, dtype=np.int)

    def elems_in_blk(self, elem_blk_id):
        """Return a list of elements in block elem_blk_id

        Parameters
        ----------
        elem_blk_id : int
            Element block ID

        Returns
        -------
        elem_list : ndarray
            Array of element IDs in elem_blk_id

        """
        i = self.setidx(PX_ELEM_BLK, elem_blk_id)
        if i is None:
            raise ExodusIIFileError("{0}: not a valid element block "
                                    "ID".format(elem_blk_id))

        # number of elements in blocks preceding elem_blk_id
        n = sum(len(x) for x in self.connect[:i])

        # element IDs for elements in elem_blk_id
        elem_ids = np.array([n + i for i in range(len(self.connect[i]))])
        elem_ids = elem_ids
        return self.elem_num_map[elem_ids]


class ExodusIIWriter(Genesis):
    """The ExodusIIWriter class

    """
    def __init__(self, runid, d=None):
        """Instantiate the ExodusIIWriter object

        Parameters
        ----------
        runid : str
            run ID, usually file basename

        Notes
        -----
        The ExodusIIFile class is an interface to the Exodus II api
        Its methods are named after the analogous method from the
        Exodus II C bindings, minus the prefix 'ex_'.

        """
        super(ExodusIIWriter, self).__init__(runid, d=d)

        # time
        self.db.createDimension(DIM_TIME, None)
        self.db.createVariable(VAR_WHOLE_TIME, DTYPE_FLT, (DIM_TIME,))

    # ----------------------------------------------------- EXODUS OUTPUT --- #
    def put_var_param(self, var_type, num_vars):
        """Writes the number of global, nodal, nodeset, sideset, or element
        variables that will be written to the database.

        Parameters
        ----------
        var_type : str
            Character indicating the type of variable which is described.
            Use one of the following options:
              "g" (or "G")
              "n" (or "N")
              "e" (or "E")
              "m" (or "M")
              "s" (or "S")
            For global, nodal, element, nodeset variables, and sideset
            variables, respectively.

        num_vars : int
            The number of var_type variables that will be written to the
            database.

        """
        dim = PX_DIM_VARS(var_type)
        self.db.createDimension(dim, num_vars)
        return

    def put_var_names(self, var_type, num_vars, var_names):
        """Writes the names of the results variables to the database. The
        names are MAX_STR_LENGTH-characters in length.

        Parameters
        ----------


        Notes
        -----
        The function put_var_param must be called before this function is
        invoked.

        """
        var_type = var_type.upper()
        var_names = ["{0:{1}s}".format(x, MAX_STR_LENGTH)[:MAX_STR_LENGTH]
                     for x in var_names]

        # store the names
        if var_type == PX_VAR_GLO:
            self.db.createVariable(VAR_NAME_GLO_VAR, DTYPE_TXT,
                                   (PX_DIM_VARS(var_type), DIM_STR))
            self.db.createVariable(VAR_GLO_VAR, DTYPE_FLT,
                                   (DIM_TIME, DIM_NUM_GLO_VAR))
        elif var_type == PX_VAR_NOD:
            self.db.createVariable(VAR_NAME_NOD_VAR, DTYPE_TXT,
                                   (PX_DIM_VARS(var_type), DIM_STR))
        elif var_type == PX_VAR_ELE:
            self.db.createVariable(VAR_NAME_ELE_VAR, DTYPE_TXT,
                                   (PX_DIM_VARS(var_type), DIM_STR))

        for (i, var_name) in enumerate(var_names):
            if var_type == PX_VAR_GLO:
                self.db.variables[VAR_NAME_GLO_VAR][i, :] = var_name

            elif var_type == PX_VAR_NOD:
                self.db.variables[VAR_NAME_NOD_VAR][i, :] = var_name
                self.db.createVariable(VAR_NOD_VAR_NEW(i+1), DTYPE_FLT,
                                       (DIM_TIME, DIM_NUM_NODES))

            elif var_type == PX_VAR_ELE:
                self.db.variables[VAR_NAME_ELE_VAR][i, :] = var_name
                for j in range(self.db.dimensions[DIM_NUM_EL_BLK]):
                    self.db.createVariable(VAR_ELEM_VAR(i+1, j+1), DTYPE_FLT,
                                           (DIM_TIME, DIM_NUM_EL_IN_BLK(j+1)))

    def put_elem_var_tab(self, num_elem_blk, num_elem_var, elem_var_tab):
        """Writes the EXODUS II element variable truth table to the database.

        The element variable truth table indicates whether a particular
        element result is written for the elements in a particular element
        block. A 0 (zero) entry indicates that no results will be output for
        that element variable for that element block. A non-zero entry
        indicates that the appropriate results will be output.

        Parameters
        ----------
        num_elem_blk : int
            The number of element blocks.

        num_elem_var : int
            The number of element variables.

        elem_var_tab : array_like, (num_elem_blk, num_elem_var)
             A 2-dimensional array containing the element variable truth
             table.

        Notes
        -----
        Although writing the element variable truth table is optional, it is
        encouraged because it creates at one time all the necessary netCDF
        variables in which to hold the EXODUS element variable values. This
        results in significant time savings. See Appendix A for a discussion
        of efficiency issues. Calling the function put_var_tab with an
        object type of "E" results in the same behavior as calling this
        function.

        The function put_var_param (or EXPVP for Fortran) must be called
        before this routine in order to define the number of element
        variables.

        """
        if num_elem_blk != self.db.dimensions[DIM_NUM_EL_BLK]:
            raise ExodusIIFileError("wrong num_elem_blk")
        if num_elem_var != self.db.dimensions[DIM_NUM_ELE_VAR]:
            raise ExodusIIFileError("wrong num_elem_var")
        self.db.createVariable(VAR_ELEM_TAB, DTYPE_INT,
                               (DIM_NUM_EL_BLK, DIM_NUM_ELE_VAR))
        for i in range(self.db.dimensions[DIM_NUM_EL_BLK]):
            self.db.variables[VAR_ELEM_TAB][i] = elem_var_tab[i]
        return

    def put_time(self, time_step, time_value):
        """Writes the time value for a specified time step.

        Parameters
        ----------
        time_step : int
            The time step number.
            This is essentially a counter that is incremented only when
            results variables are output to the data file. The first time step
            is 1.

        time_value : float
            The time at the specified time step.

        """
        self.db.variables[VAR_WHOLE_TIME][time_step] = time_value
        return

    def put_glob_vars(self, time_step, num_glo_var, vals_glo_var):
        """Writes the values of all the global variables for a single time step.

        time_step : int
            The time step number, as described under put_time.
            This is essentially a counter that is incremented when results
            variables are output. The first time step is 1.

        num_glob_vars : int
            The number of global variables to be written to the database.

        glob_var_vals : array_like
            Array of num_glob_vars global variable values for the time_stepth
            time step.

        Notes
        -----
        The function put_var_param must be invoked before this call is made.

        """
        self.db.variables[VAR_GLO_VAR][time_step, :num_glo_var] = vals_glo_var
        return

    def put_nodal_var(self, time_step, nodal_var_index, num_nodes,
                      nodal_var_vals):
        """Writes the values of a single nodal variable for a single time
        step.

        Parameters
        ----------
        time_step : int
            The time step number, as described under put_time. This is
            essentially a counter that is incremented when results variables
            are output. The first time step is 1.

        nodal_var_index : int
            The index of the nodal variable.
            The first variable has an index of 1.

        num_nodes : int
            The number of nodal points.

        nodal_var_vals : array_like
            Array of num_nodes values of the nodal_var_indexth nodal variable
            for the time_stepth time step.

        Notes
        -----
        The function put_var_param must be invoked before this call is made.

        """
        name = VAR_NOD_VAR_NEW(nodal_var_index+PX_OFFSET)
        self.db.variables[name][time_step, :num_nodes] = nodal_var_vals
        return

    def put_elem_var(self, time_step, elem_var_index, elem_blk_id,
                     num_elem_this_blk, elem_var_vals):
        """Writes the values of a single elemental variable for a single time
        step.

        Parameters
        ----------
        time_step : int
            The time step number, as described under put_time. This is
            essentially a counter that is incremented when results variables
            are output. The first time step is 1.

        elem_var_index : int
            The index of the element variable.
            The first variable has an index of 1.

        elem_blk_id : int
            The element block ID

        num_elem_this_blk : int
            The number of elements in the given element block

        elem_var_vals : array_like
            Array of num_elem_this_blk values of the elem_var_indexth element
            variable for the element block with ID of elem_blk_id at the
            time_stepth time step

        Notes
        -----
        The function put_var_param must be invoked before this call is
        made.

        It is recommended, but not required, to write the element variable
        truth table before this function is invoked for better efficiency.

        """
        name, dim = PX_PROPINFO(EX_ELEM_BLOCK)
        elem_blk_id = int(elem_blk_id)
        i = self.get_obj_idx(PX_ELEM_BLK, elem_blk_id)
        if i is None:
            raise ExodusIIFileError("bad element block ID")
        name = VAR_ELEM_VAR(elem_var_index+PX_OFFSET, i+PX_OFFSET)
        self.db.variables[name][time_step, :num_elem_this_blk] = elem_var_vals
        return

class ExodusIIFile(object):
    def __new__(cls, runid, mode="r", d=None):
        if mode not in "rw":
            raise ExodusIIFileError("{0}: bad read/write mode".format(mode))
        if mode == "w":
            return ExodusIIWriter(runid, d=d)
        filepath = runid
        if not os.path.isfile(filepath):
            filepath = runid + ".exo"
        return ExodusIIReader(filepath)
