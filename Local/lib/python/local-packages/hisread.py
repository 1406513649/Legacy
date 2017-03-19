#!/usr/bin/env python

import os, sys
import string
import array
import fnmatch

version = 1.4

help_string = """
NAME
      hisread.py - history output file reader, version """ + str(version) + """

SYNOPSIS
      hisread.py [OPTIONS] <filename>

DESCRIPTION
      The command line mode for 'hisread.py' extracts specified variable
      values from a given file name and writes them to stdout in tabular
      form.  If no variable specifications are given, then the file meta data
      is written instead.

      If a particular time value or time step is chosen, no labels are written.

      The variable specifications are matched case insensitive.  Also, dashes
      underscores, and spaces are all treated the same.

      Shell type wildcard characters can be used in the id and variable name
      specifications.  Even in this case, a lower case conversion is done on
      the pattern and the variable names in order to do case insensitive
      matching.  But dashes and underscores are treated literally here.

OPTIONS
      -h, --help
           Print man page then exit.
      -V, --version
           Print version number and exit.
      -p, --point <point id>/<variable name>
           Select a tracer point id and variable name to extract.
      -m, --material <material id>/<variable name>
           Select a material id and variable name to extract.
      -g, --global <variable name>
           Select a mesh global variable name to extract.
      -t, --time <float>
           Output the variable at this time.  Closest time value is chosen.
      -i, --index <integer>
           Output the variable at this time step index.  A value of -1 means
           the last time step in the file.
      -c, --cycle <integer>
           Output the variable at this cycle number.  Numbers start at zero.
           A value of -1 means the last time step in the file.
      --nolabels
           Do not write the variable names and units to the output.

TODO
      Add time step skipping.
      Handle multiple files (restart files) and remove any overlap.
      Maybe add other output formats, like CSV or XMGR.
"""


POINTID        = 0
POINTVAR       = 1
MATID          = 2
MATVAR         = 3
GLOBVAR        = 4
POINTVAR_UNITS = 5
MATVAR_UNITS   = 6
GLOBVAR_UNITS  = 7

title_length = 80
QA_length = 38
valid_codes = [ -100, -101, -102, -103 ]

__stream__ = sys.stdout

class HistoryData:

    def __init__(self, filename=None, skipval=None ):

        self.title = ''
        self.filename = filename
        self.skipval = skipval

        # make this false to avoid removing duplicates
        self.nodups = 1

        # indexed by POINTID, POINTVAR, MATID, MATVAR, GLOBVAR,
        # POINTVAR_UNITS, MATVAR_UNITS, GLOBVAR_UNITS;  the lists contain ids
        # and variable names for each type of data; the point ids are actually
        # pairs of (id,type)
        self.vars = [ [], [], [], [], [], [], [], [] ]

        self.cycles = []
        self.times = []
        self.timesteps = []
        self.cputimes = []

        # each entry is a list of length len(self.vars[POINTID])
        # and each of those a list of length len(self.vars[POINTVAR])
        self.point_values = []

        # each entry is a list of length len(self.vars[MATID])
        # and each of those a list of length len(self.vars[MATVAR])
        self.mat_values = []

        # each entry is a list of length len(self.vars[GLOBVAR])
        self.glob_values = []

        if filename != None:
          self.read( filename )

    def getList(self, var_type):
        """
        Use POINTID, POINTVAR, POINTVAR_UNITS, MATID, MATVAR, MATVAR_UNITS,
        GLOBVAR, or GLOBVAR_UNITS.  Returns a list of (id,type) for POINTID,
        ids for MATID, and string names for others.
        """
        return self.vars[var_type]

    def getUnitsList(self, var_type):
        """
        Use POINTVAR, MATVAR, or GLOBVAR.  Returns a list of unit strings for
        the given variable type.
        """
        if var_type == POINTVAR:
          return self.vars[POINTVAR_UNITS]
        elif var_type == MATVAR:
          return self.vars[MATVAR_UNITS]

        assert var_type == GLOBVAR, \
               "var_type must be POINTVAR, MATVAR, or GLOBVAR"
        return self.vars[GLOBVAR_UNITS]

    def getTimeValues(self):
        return self.times

    def getCycles(self):
        """
        Returns a list of the cycle numbers for each time dump.
        """
        return self.cycles

    def getValues(self, var_type, var_index, id_index=None):
        """
        The var_type can be POINTVAR, MATVAR, and GLOBVAR.
        The id_index must be supplied for POINTVAR and MATVAR.
        Returns a list of variable values of the given type of data for the
        given variable index for the given id index over all time steps.
        """
        if var_type == POINTVAR:
          assert id_index >= 0 and id_index < len(self.vars[POINTID])
          assert var_index >= 0 and var_index < len(self.vars[POINTVAR])
          vals = []
          for pL in self.point_values:
            vals.append( pL[id_index][var_index] )
          return vals
        elif var_type == MATVAR:
          assert id_index >= 0 and id_index < len(self.vars[MATID])
          assert var_index >= 0 and var_index < len(self.vars[MATVAR])
          vals = []
          for mL in self.mat_values:
            vals.append( mL[id_index][var_index] )
          return vals
        assert var_type == GLOBVAR
        assert var_index >= 0 and var_index < len(self.vars[GLOBVAR])
        vals = []
        for gL in self.glob_values:
          vals.append( gL[var_index] )
        return vals

    def read(self, filename):
        """
        Look at the first fortran record for a valid (negative) code.
        Try four and eight byte fortran padding and little and big endian.
        Raises an IOError if the platform could not be (uniquely) determined.
        """
        self.filename = filename

        fp = open( filename, 'rb' )
        rdr = Reader(fp)

        have_cycle = 0
        have_time = 0
        have_dt = 0
        have_cpu = 0

        num_dumps = 0

        while 1:

          name, data = rdr.next()

          if name == None:
            break

          if name == 'title':
            self.title = data

          elif name == 'QA':
            self.QA = data

          elif name == 'counts':
            num_points     = data[0]
            num_point_vars = data[1]
            num_mats       = data[2]
            num_mat_vars   = data[3]
            num_glob_vars  = data[4]

          elif name == 'names':
            self.vars[POINTVAR      ] = data[0]
            self.vars[POINTVAR_UNITS] = data[1]
            self.vars[MATVAR        ] = data[2]
            self.vars[MATVAR_UNITS  ] = data[3]
            self.vars[GLOBVAR       ] = data[4]
            self.vars[GLOBVAR_UNITS ] = data[5]

            for i in range(len(data[6])):
              self.vars[POINTID].append( (data[6][i], data[7][i]) )
            for m in data[8]:
              self.vars[MATID].append( m )

            for n in self.vars[GLOBVAR]:
              if n == "CYCLE": have_cycle = 1
              if n == "TIME": have_time = 1
              if n == "DT": have_dt = 1
              if n == "CPU": have_cpu = 1

            if not have_cycle:
              self.vars[GLOBVAR].append( "CYCLE" )
              self.vars[GLOBVAR_UNITS].append( "" )
            if not have_time:
              self.vars[GLOBVAR].append( "TIME" )
              self.vars[GLOBVAR_UNITS].append( "S" )
            if not have_dt:
              self.vars[GLOBVAR].append( "DT" )
              self.vars[GLOBVAR_UNITS].append( "S" )
            if not have_cpu:
              self.vars[GLOBVAR].append( "CPU" )
              self.vars[GLOBVAR_UNITS].append( "S" )

          else:

            cycle, time, timestep, cpu, ra = data

            idx = 0

            pvals = []
            for i in range(num_points):
              pvals.append( ra[idx:idx+num_point_vars].tolist() )
              idx = idx + num_point_vars

            mvals = []
            for i in range(num_mats):
              mvals.append( ra[idx:idx+num_mat_vars].tolist() )
              idx = idx + num_mat_vars

            gvals = ra[idx:].tolist()
            if not have_cycle: gvals.append( cycle )
            if not have_time:  gvals.append( time )
            if not have_dt:    gvals.append( timestep )
            if not have_cpu:   gvals.append( cpu )

            if num_dumps == 0 or self.skipval == None or \
                self.skipval <= 0 or num_dumps%self.skipval == 0:
              self._removeRepeats( cycle )
              self.cycles.append( cycle )
              self.times.append( time )
              self.timesteps.append( timestep )
              self.cputimes.append( cpu )
              self.point_values.append( pvals )
              self.mat_values.append( mvals )
              self.glob_values.append( gvals )

            num_dumps = num_dumps + 1

        fp.close()

    def _removeRepeats(self, newcycle):
        popcount = 0
        if self.nodups and len(self.cycles) > 0:
          i = -1
          while (-i) <= len(self.cycles) and newcycle <= self.cycles[i]:
            popcount = popcount + 1
            i = i - 1
        if popcount > 0:
          for i in range(popcount):
            self.cycles.pop(-1)
            self.times.pop(-1)
            self.timesteps.pop(-1)
            self.cputimes.pop(-1)
            self.point_values.pop(-1)
            self.mat_values.pop(-1)
            self.glob_values.pop(-1)


#########################################################################
#
#   Convenience functions
#

    def getWriteIndex(self, cycle, write_cycle, time):
        """
        """

        if not cycle==None:
          try:
            write_index = self.getCycles().index(cycle)
          except:
            message("Failed to find cycle " + str(cycle) +
                    " in file " + filename)
        elif not write_cycle==None:
          try:
            # To get the first time written, write_cycle=0;
            # this allows us to get the last time with write_cycle=-1
            write_index = self.getCycles()[write_cycle]
          except:
            message("Failed to find write_cycle " + str(write_cycle) +
                    " in file " + filename)
        elif not time==None:   # Need to add a tolerance here, no?
          try:
            write_index = self.getTimeValues().index(time)
          except:
            message("Failed to find time " + str(time) + " in file " + filename)

        return write_index

    def getGlobalVar(self, varname,
                     cycle=None, time=None, write_cycle=None,
                     units=False):
        """Open a hisplot file and get the value or values of the
        global variable requested.

        Inputs:
        varname      the (string) name of the global variable
        cycle        get the value for a particular cycle
        time         get the value for a particular time
        write_cycle  get the value for a particular write
        units        add units to the output

        The cycle refers to the computational cycle of the simulation. Often
        the output is written to a hisplot file at a lower frequency than
        every cycle, and write_cycle refers to the nth write to the file.
        The time refers to a particular simulation time. Only one of cycle,
        write_cycle, or time can be specified.

        Returns:
        If cycle, time, and write_id are all None (the default), a list
        containing the variable values is returned.
        If any of cycle, time, or write_id is specified, only the corresponding
        variable value is returned
        If units is True, then a tuple is returned. The first entry is the
        list of values or the value, and the second is a string containing
        the units.
        """

        try:
          gv_index = self.getList(GLOBVAR).index(varname)
        except:
          error("Failed to find global variable " + varname +
                " in file " + self.filename)

        if units:
          unit_string = self.getUnitsList(GLOBVAR)[gv_index]

        count = 0
        if not cycle==None:  count+=1
        if not write_cycle==None:  count+=1
        if not time==None:  count+=1
        if count>1:
          error("Can only specify one of cycle, write_cycle, and time.")

        # Do we need to find a particular cycle/write_cycle/time? If so find it
        if count==1:

          write_index = self.getWriteIndex(cycle, write_cycle, time)
          varval = self.getValues(GLOBVAR, gv_index)[write_index]

          if units:
            return varval, unit_string
          else:
            return varval

        # otherwise just return all the values
        else:
          varvals = self.getValues(GLOBVAR, gv_index)
          if units:
            return varvals, unit_string
          else:
            return varvals

    def getTracerVar(self, varname, tracer_id,
                     cycle=None, time=None, write_cycle=None,
                     units=False):
        """Open a hisplot file and get the value or values of the
        tracer variable requested.

        Inputs:
        varname      the (string) name of the global variable
        tracer_id    the id (int) of the tracer
        cycle        get the value for a particular cycle
        time         get the value for a particular time
        write_cycle  get the value for a particular write
        units        add units to the output

        The cycle refers to the computational cycle of the simulation. Often
        the output is written to a hisplot file at a lower frequency than
        every cycle, and write_cycle refers to the nth write to the file.
        The time refers to a particular simulation time. Only one of cycle,
        write_cycle, or time can be specified.

        Returns:
        If cycle, time, and write_id are all None (the default), a list
        containing the variable values is returned.
        If any of cycle, time, or write_id is specified, only the corresponding
        variable value is returned
        If units is True, then a tuple is returned. The first entry is the
        list of values or the value, and the second is a string containing
        the units.
        """

        try:
          var_index = self.getList(POINTVAR).index(varname)
        except:
          error("Failed to find tracer variable " + varname +
                " in file " + self.filename)

        try:
          tvL = self.getList(POINTID)
          found = False
          for tracer in tvL:
            if tracer_id == tracer[0]:
              id_index = tvL.index(tracer)
              found = True
              break
          assert(found)
        except:
          error("Failed to find tracer " + str(tracer_id) +
                " in file " + self.filename)

        if units:
          unit_string = self.getUnitsList(POINTVAR)[var_index]

        count = 0
        if not cycle==None:  count+=1
        if not write_cycle==None:  count+=1
        if not time==None:  count+=1
        if count>1:
          error("Can only specify one of cycle, write_cycle, and time.")

        # Do we need to find a particular cycle/write_cycle/time? If so find it
        if count==1:

          write_index = self.getWriteIndex(cycle, write_cycle, time)
          varval = self.getValues(POINTVAR, var_index, id_index)[write_index]

          if units:
            return varval, unit_string
          else:
            return varval

        # otherwise just return all the values
        else:
          varvals = self.getValues(POINTVAR, var_index, id_index)
          if units:
            return varvals, unit_string
          else:
            return varvals

    def getMaterialVar(self, varname,
                     cycle=None, time=None, write_cycle=None,
                     units=False):
        """Open a hisplot file and get the value or values of the
        material variable requested.

        Inputs:
        varname      the (string) name of the material variable
                       (the last characters should be the material id)
        cycle        get the value for a particular cycle
        time         get the value for a particular time
        write_cycle  get the value for a particular write
        units        add units to the output

        The cycle refers to the computational cycle of the simulation. Often
        the output is written to a hisplot file at a lower frequency than
        every cycle, and write_cycle refers to the nth write to the file.
        The time refers to a particular simulation time. Only one of cycle,
        write_cycle, or time can be specified.

        Returns:
        If cycle, time, and write_id are all None (the default), a list
        containing the variable values is returned.
        If any of cycle, time, or write_id is specified, only the corresponding
        variable value is returned
        If units is True, then a tuple is returned. The first entry is the
        list of values or the value, and the second is a string containing
        the units.
        """

        mat_id_string = varname.split("-")[-1]
        ndig = len(mat_id_string)
        matvarbase = varname[:-ndig]
        try:
         assert(mat_id_string.isdigit())
        except:
          error("The material variable " + varname + " does not end in digits."
                + "Is it a material variable?")

        try:
          var_index = self.getList(MATVAR).index(matvarbase)
        except:
          error("Failed to find material variable " + matvarbase +
                " in file " + self.filename)

        mat_id=int(mat_id_string)

        try:
          id_index = self.getList(MATID).index(mat_id)
        except:
          error("Failed to find material " + mat_id_string +
                " in file " + self.filename)

        if units:
          unit_string = self.getUnitsList(MATVAR)[var_index]

        count = 0
        if not cycle==None:  count+=1
        if not write_cycle==None:  count+=1
        if not time==None:  count+=1
        if count>1:
          error("Can only specify one of cycle, write_cycle, and time.")

        # Do we need to find a particular cycle/write_cycle/time? If so find it
        if count==1:

          write_index = self.getWriteIndex(cycle, write_cycle, time)
          varval = self.getValues(MATVAR, var_index, id_index)[write_index]

          if units:
            return varval, unit_string
          else:
            return varval

        # otherwise just return all the values
        else:
          varvals = self.getValues(MATVAR, var_index, id_index)
          if units:
            return varvals, unit_string
          else:
            return varvals


class Reader:
    """
    Class to iterate the contents of a hisplt file.  Create an instance
    with an open file object, then call the next() method until (None,None) is
    returned.  For example,

      fp = open('somefile.his','r')
      rdr = Reader(fp)
      while 1:
        name,data = rdr.next()
        if name == None:
          break
        elif name == "title":
          ...
        elif name == "QA":
          ...
        elif name == "counts":
          ...
        elif name == "names":
          ...
        elif name == "cycle":
          ...
      fp.close()

    The name values are:

      "title" : the data is a title string
      "QA"    : the data is a QA string
      "counts": the data is a tuple (in order):
                      num points, num point vars,
                      num mats, num mat vars,
                      num global vars
      "names" : the data is a tuple containing (in order):
                      point var names, point unit names,
                      mat var names, mat unit names,
                      global var names, global unit names,
                      point integers, point type integers,
                      material integers
      "cycle" : the data is a tuple (in order):
                      cycle number,
                      time value,
                      time step size,
                      CPU time,
                      array.array() of type 'f' containing the variable values
                the variable values are stored in this order
                      idx = 0
                      for each point:
                        for each point variable:
                          point var value = array[idx]
                          idx = idx + 1
                      for each material:
                        for each mat variable:
                          material var value = array[idx]
                          idx = idx + 1
                      for each global variable:
                        gloval var value = array[idx]
                        idx = idx + 1
    """

    def __init__(self, fp):
        """
        The argument must be an open file object still pointing at the start
        of the file.
        """
        self.fp = fp
        self.swap = None
        self.pad = None
        self.counts = None  # tuple of (num words, num points, num point vars,
                            #           num mats, num mat vars, num globals)
        self.num_cycles = 0

    def next(self):
        """
        Returns (None,None) if at end of file.
        """
        ra = array.array('f')

        if self.swap == None:

          # check for a valid icode with 4 byte padding first

          s = self.fp.read( 5*4 )  # first 5 4-byte words
          a1 = array.array('i');
          a1.fromstring( s[-4:] )  # try to get icode from 5-th word
          if a1[0] in valid_codes:
            self.pad = 4
            self.swap = 0
            ra.fromstring( s[4:-4] )
            icode = a1[0]
          else:
            # try byte swapping 5-th word
            a1.byteswap()
            if a1[0] in valid_codes:
              self.pad = 4
              self.swap = 1
              ra.fromstring( s[4:-4] )
              ra.byteswap()
              icode = a1[0]
            else:
              # check for a valid icode with 8 byte padding
              a2 = array.array('i');
              a2.fromfile( self.fp, 1 )
              if a2[0] in valid_codes:
                self.pad = 8
                self.swap = 0
                ra.fromstring( s[8:] )
                icode = a2[0]
              else:
                # try byte swapping 6-th word
                a2.byteswap()
                if a2[0] in valid_codes:
                  self.pad = 8
                  self.swap = 1
                  ra.fromstring( s[8:] )
                  ra.byteswap()
                  icode = a2[0]
                else:
                  raise IOError( 'hisread.py: unable to determine fortran ' + \
                                 'padding and byte order' )

        else:
          # read the beginning pad for the next fortran record
          if len( self.fp.read( self.pad ) ) != self.pad:
            return None, None

          # read the first three floats = time, time step, cpu time
          ra = array.array('f')
          ra.fromfile( self.fp, 3 )
          if self.swap: ra.byteswap()

          # then read the dump number/code
          icode = array.array('i')
          icode.fromfile(self.fp, 1)
          if self.swap: icode.byteswap()
          icode = icode[0]

        # try to adjust if infinities are read in
        if 1.e30 < ra[0] and ra[0] + ra[0] == ra[0]: ra[0] = 1.e30
        if 1.e30 < ra[1] and ra[1] + ra[1] == ra[1]: ra[1] = 1.e30

        #print "hisread code", icode

        if icode == -100:  # title record

          # skip the rest of the record, its trailing pad, and the beginning
          # pad for the next record
          self.fp.read( 12 + 2 * self.pad )

          # then read the title string (fixed size of 80 characters)
          s = string.strip( self.fp.read( title_length ) )
          self.fp.read( self.pad )  # skip pad at end of the fortran record

          return 'title',s

        if icode == -101:  # QA record

          # a little ugly here; it seems if a cycle record  has already been
          # written, then we need to skip over a cycle record's worth of data
          # first

          if self.num_cycles == 0:
            # skip the rest of the record, its trailing pad, and the
            # beginning pad for the next record, then read the QA string
            self.fp.read( 12 + 2 * self.pad )
            s = self.fp.read( QA_length )
          else:
            # skip the pad of the record, beginning pad of the next record,
            # then skip over the size of a full cycle record
            self.fp.read( 2 * self.pad )
            a = array.array('f')
            a.fromfile( self.fp, self.counts[0] )
            s = self.fp.read( QA_length )  # read the QA string

          self.fp.read( self.pad )  # skip pad at end of the record

          return 'QA', string.strip(s)

        if icode == -102:  # the number of variables of each type

          # skip the rest of the record, its trailing pad, and the
          # beginning pad for the next record
          self.fp.read( 12 + 2 * self.pad )

          # order in file: num points, num mats, num point vars,
          #                num mat vars, num glob vars
          ia = array.array('i')
          ia.fromfile( self.fp, 5 )
          if self.swap: ia.byteswap()
          n = ia[0]*ia[2] + ia[1]*ia[3] + ia[4]
          # save counts
          #   0: number of floats to store a cycle dump
          #   1: num points
          #   2: num point vars
          #   3: num materials
          #   4: num material vars
          #   5: num global vars
          self.counts = ( n, ia[0], ia[2], ia[1], ia[3], ia[4] )

          self.fp.read( self.pad )  # skip pad at end of the record

          return 'counts', (ia[0], ia[2], ia[1], ia[3], ia[4])

        if icode == -103:  # the variable and unit names

          if self.counts == None:
            raise IOError( "hisread.py: a variable names record found " + \
                           "before a variable counts record (corrupt file?)" )

          # it appears as though all the variables are written to
          # the record even though the names have not been read yet.
          # skip through them to get to the end of the current record
          a = array.array('f')
          a.fromfile( self.fp, self.counts[0] )

          # read past trailing pad and the beginning pad for the next record
          self.fp.read( 2 * self.pad )

          # read the variable names and units (each has fixed length of 16)
          n = self.counts[2] + self.counts[4] + self.counts[5]
          vstr = self.fp.read( 2*n*16 )

          def getvars( s, idx, num ):
              varL = []
              for i in range(num):
                varL.append( string.join( string.split( s[idx:idx+16] ) ) )
                idx = idx + 16
              return idx, varL

          # point vars, mat vars, global vars, then units for each
          i, pvL = getvars( vstr, 0, self.counts[2] )  # point vars
          i, mvL = getvars( vstr, i, self.counts[4] )  # material vars
          i, gvL = getvars( vstr, i, self.counts[5] )  # global vars
          i, puL = getvars( vstr, i, self.counts[2] )  # point units
          i, muL = getvars( vstr, i, self.counts[4] )  # material units
          i, guL = getvars( vstr, i, self.counts[5] )  # global units

          # read the point numbers & types and material numbers
          ia = array.array('i')
          ia.fromfile( self.fp, 2*self.counts[1] + self.counts[3] )
          if self.swap: ia.byteswap()
          L = ia.tolist()
          pL = L[:self.counts[1]]
          mL = L[self.counts[1]:self.counts[1]+self.counts[3]]
          tL = L[self.counts[1]+self.counts[3]:]

          self.fp.read( self.pad )  # skip pad at end of the record

          return 'names', (pvL, puL, mvL, muL, gvL, guL, pL, tL, mL)

        if icode < 0:  # unknown code
          raise IOError( "*** hisread.py: unknown code:" + str(icode) + \
                         " (corrupt file?)" )

        # cycle record; icode is the cycle number

        if self.counts == None:
          raise IOError( "hisread.py: a cycle record found " + \
                           "before a variable counts record (corrupt file?)" )

        self.num_cycles = self.num_cycles + 1

        a = array.array('f')
        try:
          a.fromfile( self.fp, self.counts[0] )
        except Exception, e:
          raise IOError( "hisread.py: failed to read cycle data for cycle " + \
                         str(icode) + ": " + str(e) )
        if self.swap: a.byteswap()

        self.fp.read( self.pad )  # skip pad at end of the record

        return 'cycle', (icode, ra[0], ra[1], ra[2], a)


#########################################################################
def error(message):
    sys.exit("*** hisread.py error: %s\n" % (message))

def message(message):
    sys.stdout.write("%s\n" % message)

def log_to_stream(message, nl="\n"):
    __stream__.write("%s%s" % (message.rstrip(), nl))

def meta_data( opts, fileL ):
    """
    Writes out the point & material ids and the point, material, and global
    variable names for each file in the list.
    """
    for f in fileL:
      fp = open( f, 'rb' )
      rdr = Reader( fp )
      ncycles = 0
      neednl = 0
      prev_cycle = -1000
      log_to_stream("File: %s\n" % (f))
      while 1:
        name,data = rdr.next()
        if name == None:
          break
        if name == "title":
          log_to_stream("Title: %s\n" % (data))
          neednl = 0
        elif name == "QA":
          if neednl: log_to_stream( os.linesep )
          log_to_stream("QA: %s\n" % (data))
          neednl = 0
        elif name == "counts":
          log_to_stream("Num points            : %s\n" % (str(data[0])))
          log_to_stream("Num points variables  : %s\n" % (str(data[1])))
          log_to_stream("Num materials         : %s\n" % (str(data[2])))
          log_to_stream("Num material variables: %s\n" % (str(data[3])))
          log_to_stream("Num global variables  : %s\n" % (str(data[4])))
          neednl = 0
        elif name == "names":
          log_to_stream("Point ids: %s\n" % (
                  string.join( map( lambda x: str(x), data[6] ) )))
          log_to_stream("Point variables:\n")
          for i in range(len(data[0])):
            log_to_stream("  %s [%s]\n" % (data[0][i], data[1][i]))
          log_to_stream("Material ids: %s\n" % (
                  string.join( map( lambda x: str(x), data[8] ) )))
          log_to_stream("Material variables:\n")
          for i in range(len(data[2])):
            log_to_stream("   %s [%s]\n" % (str(data[2][i]), str(data[3][i])))
          log_to_stream("Global variables:\n")
          for i in range(len(data[4])):
            log_to_stream( "   %s [%s]\n" % (str(data[4][i]), str(data[5][i])))
          neednl = 0
        elif name == "cycle" and data[0] > prev_cycle:
          ncycles = ncycles + 1
          dot = 0
          if ncycles < 10: dot = 1
          elif ncycles < 100 :
            if ncycles%10 == 0: dot = 1
          elif ncycles < 1000:
            if ncycles%100 == 0: dot = 1
          elif ncycles%1000 == 0: dot = 1
          if dot:
            log_to_stream('.', nl="")
            neednl = 1
          prev_cycle = data[0]
      fp.close()
      log_to_stream("Num cycles: %s\n" % (str(ncycles)))

def name_compare( n1, n2 ):
    """
    Case insensitive.  Strips space, '-', '_' from both ends.  Treats '-', '_'
    as a space.  Multiple spaces treated as one space.
    """
    n1 = string.lower( string.strip(n1) )
    n2 = string.lower( string.strip(n2) )
    n1 = string.strip( string.strip( n1, '-' ), '_' )
    n2 = string.strip( string.strip( n2, '-' ), '_' )
    n1 = string.join( string.split( n1 ) )
    n1 = string.join( string.split( n1, '-' ) )
    n1 = string.join( string.split( n1, '_' ) )
    n2 = string.join( string.split( n2 ) )
    n2 = string.join( string.split( n2, '-' ) )
    n2 = string.join( string.split( n2, '_' ) )
    return n1 == n2


def find_var_index( counts, names, t, i, n ):
    """
    Finds and returns the raw data index corresponding to the requested type,
    id, and name.  The type 't' can be a "g", "p", or "m" for global, point,
    or material.  For point or material, 'i' is the id.  The name 'n' is the
    variable name.  The 'counts' and 'names' must be the data that the Reader
    class returns.

    It returns a list of tuples (name, units, index) if at least one variable
    matches or None if not.  The returned index is the index or offset into the
    array data returned by the Reader for each cycle. Special index values are
    -1 for CYCLE, -2 for TIME, -3 for TIME STEP, and -4 for CPU time.
    """
    assert t in ['p','m','g']

    def direct_match( idxval, ival, ilist, nval, nlist, ulist ):
        try:
          asint = int(ival)
        except:
          pass
        else:
          for j in ilist:
            if j == asint:
              for ii in range(len(nlist)):
                vn = nlist[ii]
                if name_compare(vn, nval):
                  vu = ulist[ii]
                  return [ (str(j)+'/'+str(vn), vu, idxval) ]
                idxval = idxval + 1
              break  # point id found but not the variable name
            else:
              idxval = idxval + len(nlist)
        return None

    def pattern_match( idxval, ival, ilist, nval, nlist, ulist ):
        L = []
        lowern = string.lower(nval)
        for j in ilist:
          jstr = str(j)
          if fnmatch.fnmatch( jstr, ival ):
            for ii in range(len(nlist)):
              vn = nlist[ii]
              lowervn = string.lower( vn )
              if fnmatch.fnmatch( lowervn, lowern ):
                vu = ulist[ii]
                L.append( (jstr+'/'+vn,vu,idxval) )
              idxval = idxval + 1
          else:
            idxval = idxval + len(nlist)
        return L

    if t == 'p':
      m = direct_match( 0, i, names[6], n, names[0], names[1] )
      if m != None:
        return m
      # no match, so maybe they are using shell wildcards
      L = pattern_match( 0, i, names[6], n, names[0], names[1] )
      if len(L) > 0:
        return L

    if t == 'm':
      idx = counts[0]*counts[1]
      m = direct_match( idx, i, names[8], n, names[2], names[3] )
      if m != None:
        return m
      # no match, so maybe they are using shell wildcards
      L = pattern_match( idx, i, names[8], n, names[2], names[3] )
      if len(L) > 0:
        return L

    if t == 'g':
      idx = counts[0]*counts[1] + counts[2]*counts[3]
      for ii in range(len(names[4])):
        vn = names[4][ii]
        if name_compare(vn, n):
          vu = names[5][ii]
          return [ (vn, vu, idx) ]
        idx = idx + 1
      # check for special variable names
      if name_compare( "cycle", n ):
        return [ ( "CYCLE", "[ND]", -1 ) ]
      if name_compare( "time", n ):
        return [ ( "TIME", "[S]", -2 ) ]
      if name_compare( "time step", n ) or name_compare( "dt", n ):
        return [ ( "TIME STEP", "[S]", -3 ) ]
      if name_compare( "cpu", n ):
        return [ ( "CPU", "[S]", -4 ) ]
      # no match, so maybe they are using shell wildcards
      idx = counts[0]*counts[1] + counts[2]*counts[3]
      lowern = string.lower(n)
      L = []
      for ii in range(len(names[4])):
        vn = names[4][ii]
        lowervn = string.lower(vn)
        if fnmatch.fnmatch( lowervn, lowern ):
          vu = names[5][ii]
          L.append( (vn, vu, idx) )
        idx = idx + 1
      if len(L) > 0:
        return L

    return None


def extract_data( opts, varL, fileL ):
    """
    Finds the variables in the file and writes the values out in tabular
    format to stdout.
    """
    assert len(fileL) == 1, "multiple files not supported yet"

    f = fileL[0]

    fp = open( f, 'rb' )
    rdr = Reader( fp )

    counts = None
    names = None
    variL = []  # index into raw data array
    prev_cycle = -1000  # used to ignore repeats

    tval = None
    ival = None
    cval = None
    if opts.has_key('-t'):
      tval = opts['-t']
    elif opts.has_key('-i'):
      ival = opts['-i']
    elif opts.has_key('-c'):
      cval = opts['-c']
    prev_time = None
    prev_data = None
    written = 0

    alldata = []
    def writeout( viL, dta ):
        L = []
        _dta = []
        for i in viL:
          _a = None
          if i < 0:
            if   i == -1: _a = dta[0] # cycle
            elif i == -2: _a = dta[1] # time
            elif i == -3: _a = dta[2] # time step
            elif i == -4: _a = dta[3] # cpu time
          else:
            _a = dta[4][i]
          if _a is not None:
            L.append( "%-20.16e"%_a )
            _dta.append(_a)
        log_to_stream(" %s\n" % (string.join(L)))
        alldata.append(_dta)

    idx = 0
    while 1:
      name,data = rdr.next()
      if name == None:
        break
      if name == "counts":
        counts = data
      elif name == "names":
        if counts == None:
          error("file corrupt (names came before counts)")
        if names != None:
          error("file corrupt (multiple names records)")
        names = data
        varnL = []
        varuL = []
        for t,i,n in varL:
          vL = find_var_index( counts, names, t, i, n )
          if vL != None:
            for vn,vu,vi in vL:
              varnL.append( "%-20s"%vn )
              varuL.append( "%-20s"%vu )
              variL.append(vi)
          else:
            if t == 'g': s = n
            else: s = i + '/' + n
            error("could not find variable %s" % s)
            sys.exit(1)
        if tval == None and ival == None and cval == None and \
           not opts.has_key('--nolabels'):
          log_to_stream('# %s\n' % (string.join(varnL)))
          log_to_stream('# %s\n' % (string.join(varuL)))

      elif name == "cycle" and data[0] > prev_cycle:

        if tval != None:
          if tval <= data[1]:
            if prev_time != None and tval - prev_time < data[1] - tval:
              writeout( variL, prev_data )
            else:
              writeout( variL, data )
            written = 1
            break
        elif ival != None:
          if ival == idx:
            writeout( variL, data )
            written = 1
            break
        elif cval != None:
          if cval == data[0]:
            writeout( variL, data )
            written = 1
            break
        else:
          written = 1
          writeout( variL, data )

        prev_cycle = data[0]
        prev_time = data[1]
        prev_data = data
        idx = idx + 1

    if not written and prev_data != None:
      if cval == None or cval > prev_data[0]:
        writeout( variL, prev_data )

    fp.close()
    return alldata


def main(argv, stream=None):
  import getopt
  global __stream__
  if stream is None:
    stream = open(os.devnull, "w")
  if not isinstance(stream, file):
    error("{0} is not a file object")
  __stream__ = stream

  try:
    optL, argL = getopt.getopt( argv, "hVg:p:m:t:i:c:",
                                longopts=['help','version','point=',
                                'material=','global=','nolabels',
                                'time=','index=','cycle='] )
  except getopt.error, e:
    error(str(e))

  def idsplit(s):
    L = string.split(v,'/',1)
    if len(L) == 2 and string.strip(L[0]) and string.strip(L[1]):
      return string.strip(L[0]),string.strip(L[1])
    return None,None

  optD = {}
  varL = []
  for n,v in optL:
    if n in ['-h','--help']:
      print help_string
      sys.exit(0)
    if n in ['-V','--version']:
      print version
      sys.exit(0)
    if n == '-p' or n == '--point':
      vi,vn = idsplit(v)
      if vi == None:
        error("point specification must be 'point_id/variable_name': " + v)
      varL.append( ('p',vi,vn) )
    elif n == '-m' or n == '--material':
      vi,vn = idsplit(v)
      if vi == None:
        error("material specification must be 'material_id/variable_name': " + v)
      varL.append( ('m',vi,vn) )
    elif n == '-g' or n == '--global':
      v = string.strip(v)
      if not v:
        error("global specification cannot be empty")
      varL.append( ('g',None,v) )
    elif n in ['-t','--time']:
      try:
        f = float(v)
      except:
        error("-t or --time value must be a number")
      optD['-t'] = f
    elif n in ['-i','--index']:
      try:
        i = int(v)
      except:
        error("-i or --index value must be an integer")
      optD['-i'] = i
    elif n in ['-c','--cycle']:
      try:
        i = int(v)
      except:
        error("-c or --cycle value must be an integer")
        sys.exit(1)
      optD['-c'] = i
    else:
      optD[n] = optD.get(n,[]) + [v]

  if len(argL) == 0:
    error("expected a filename")

  if len(varL) > 0:
    return extract_data( optD, varL, argL )
  else:
    return meta_data( optD, argL )


#########################################################################
if __name__ == "__main__":
  main(sys.argv[1:], stream=sys.stdout)
