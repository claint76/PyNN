# encoding: utf-8
"""
FACETS-ML implementation of the PyNN API.
$Id$
"""

import common
#import numpy, types, sys, shutil
#import RandomArray
from xml.dom import *
from xml.dom.minidom import *
from xml.dom.ext import *

gid           = 0
ncid          = 0
gidlist       = []
vfilelist     = {}
spikefilelist = {}
dt            = 0.1
running       = False

# ==============================================================================
#   Module-specific functions and classes (not part of the common API)
# ==============================================================================


xmldoc = Document()

"""
warning :
    in order to write xml in a format which respects the namespaces, you must use xml.dom.ext.PrettyPrint
namespaces allowed are :
        neuromlNode.setAttribute('xmlns:net','http://morphml.org/networkml/schema')
        neuromlNode.setAttribute('xmlns:mml','http://morphml.org/morphml/schema')
        neuromlNode.setAttribute('xmlns:meta','http://morphml.org/metadata/schema')
        neuromlNode.setAttribute('xmlns:bio','http://morphml.org/biophysics/schema')
        neuromlNode.setAttribute('xmlns:cml','http://morphml.org/channelml/schema')

"""

def initDocument(parentElementNS,parentElementName,prefix=''):
    """
    create the root element <neuroml> if doesn't exist
    and the specified parentElement just below <neuroml> if doesn't exist
    returns the parentElement node
    """
    neuromlNodes = xmldoc.getElementsByTagNameNS('http://morphml.org/neuroml/schema','neuroml')
    #if the <neuroml> markup is not yet created
    if(neuromlNodes.length == 0):
        #neuroml has no prefix, namespace http://morphml.org/neuroml/schema is the default one
        neuromlNode = xmldoc.createElementNS('http://morphml.org/neuroml/schema','neuroml')
        xmldoc.appendChild(neuromlNode)
    else:
        neuromlNode = neuromlNodes[0]
    parentElementNodes = neuromlNode.getElementsByTagNameNS(parentElementNS,parentElementName)
    #if the <parentElementName> markup is not yet created
    if(parentElementNodes.length == 0):
        #if no prefix has been defined and the namespace of the new parent element is not the default
        # namespace, a new namespace is associated to null prefix, which is not good 
        if(prefix == ''):
            parentElementNode = xmldoc.createElementNS(parentElementNS,parentElementName)
        else:
            parentElementNode = xmldoc.createElementNS(parentElementNS,prefix + ":" + parentElementName)
        neuromlNode.appendChild(parentElementNode)
    else:
        parentElementNode = parentElementNodes[0]
    return parentElementNode

def writeDocument(url):
    """
    write the xmldoc created to a file specified by the url
    """
    file = open(url,'w')
    PrettyPrint(xmldoc, file)
    file.close()
    


# ==============================================================================
#   Utility classes
# ==============================================================================

class ID(common.ID):
    """
    This class is experimental. The idea is that instead of storing ids as
    integers, we store them as ID objects, which allows a syntax like:
      p[3,4].set('tau_m',20.0)
    where p is a Population object. The question is, how big a memory/performance
    hit is it to replace integers with ID objects?
    """
    
    def set(self,param,val=None):
        # We perform a call to the low-level function set() of the API.
        # If the cellclass is not defined in the ID object, we have an error (?) :
        if (self._cellclass == None):
            raise Exception("Unknown cellclass")
        else:
            #Otherwise we use the ID one. Nevertheless, here we have a small problem in the
            #parallel framework. Suppose a population is created, distributed among
            #several nodes. Then a call like cell[i,j].set() should be performed only on the
            #node who owns the cell. To do that, if the node doesn't have the cell, a call to set()
            #do nothing...
            ##if self._hocname != None:
            ##    set(self,self._cellclass,param,val, self._hocname)
            set(self,self._cellclass,param,val)
    
    def get(self,param):
        #This function should be improved, with some test to translate
        #the parameter according to the cellclass
        #We have here the same problem as with set() in the parallel framework
        if self._hocname != None:
            return HocToPy.get('%s.%s' %(self._hocname, param),'float')
    
    # Fonctions used only by the neuron version of pyNN, to optimize the
    # creation of networks
    def setHocName(self, name):
        self._hocname = name

    def getHocName(self):
        return self._hocname


def checkParams(param,val=None):
    """Check parameters are of valid types, normalise the different ways of
       specifying parameters and values by putting everything in a dict.
       Called by set() and Population.set()."""
    if isinstance(param,str):
        if isinstance(val,float) or isinstance(val,int):
            paramDict = {param:float(val)}
        elif isinstance(val,(str, list)):
            paramDict = {param:val}
        else:
            raise common.InvalidParameterValueError
    elif isinstance(param,dict):
        paramDict = param
    else:
        raise common.InvalidParameterValueError
    return paramDict


# ==============================================================================
#   Standard cells
# ==============================================================================

"""
As I don't really care about which CellClass is it, as I will dump its parameters
"as it" in XML, all my CellType are a wrapper around a FacetsmlCellType
The creation of default parameters is done in the common constructors
"""

class FacetsmlCellType(object):
    """Base class for facetsMLCellType"""
    
    def __init__(self,facetsml_name,parameters):
        cellsNode = initDocument('http://morphml.org/neuroml/schema','cells')
        cellNode = xmldoc.createElementNS('http://morphml.org/neuroml/schema','cell')
        self.domNode = cellNode
        cellsNode.appendChild(cellNode)
        facetsml_nameNode = xmldoc.createElementNS('http://morphml.org/neuroml/schema',facetsml_name)
        self.parameters = parameters
        # just dump "as it" the given parameters
        for k in self.parameters.keys():
            print k, self.parameters[k]
            facetsml_nameNode.setAttribute(k,str(self.parameters[k]))
        cellNode.appendChild(facetsml_nameNode)


class StandardCellType(common.StandardCellType):
    """Base class for standardized cell model classes."""
    
    facetsml_name = "StandardCellType"

    def __init__(self,parameters):
        common.StandardCellType.__init__(self,parameters)
        self.facetsmlCellType = FacetsmlCellType(facetsml_name,self.parameters)

    
class IF_curr_alpha(common.IF_curr_alpha):
    """Leaky integrate and fire model with fixed threshold and alpha-function-
    shaped post-synaptic current."""

    facetsml_name = "IF_curr_alpha"

    def __init__(self,parameters):
        common.IF_curr_alpha.__init__(self,parameters)
        self.facetsmlCellType = FacetsmlCellType(facetsml_name,self.parameters)
    

class IF_curr_exp(common.IF_curr_exp):
    """Leaky integrate and fire model with fixed threshold and
    decaying-exponential post-synaptic current. (Separate synaptic currents for
    excitatory and inhibitory synapses"""
    
    facetsml_name = "IF_curr_exp"

    def __init__(self,parameters):
        common.IF_curr_exp.__init__(self,parameters)
        self.facetsmlCellType = FacetsmlCellType(IF_curr_exp.facetsml_name,self.parameters)
    

class IF_cond_alpha(common.IF_cond_alpha):
    """Leaky integrate and fire model with fixed threshold and alpha-function-
    shaped post-synaptic conductance."""
    
    facetsml_name = "IF_cond_alpha"

    def __init__(self,parameters):
        common.IF_cond_alpha.__init__(self,parameters)
        self.facetsmlCellType = FacetsmlCellType(facetsml_name,self.parameters)

class SpikeSourcePoisson(common.SpikeSourcePoisson):
    """Spike source, generating spikes according to a Poisson process."""

    facetsml_name = "SpikeSourcePoisson"

    def __init__(self,parameters):
        common.SpikeSourcePoisson.__init__(self,parameters)
        self.facetsmlCellType = FacetsmlCellType(facetsml_name,self.parameters)

class SpikeSourceArray(common.SpikeSourceArray):
    """Spike source generating spikes at the times given in the spike_times array."""

    facetsml_name = "SpikeSourceArray"

    def __init__(self,parameters):
        common.SpikeSourceArray.__init__(self,parameters)
        self.facetsmlCellType = FacetsmlCellType(facetsml_name,self.parameters)



# ==============================================================================
#   Functions for simulation set-up and control
# ==============================================================================

def setup(timestep=0.1,min_delay=0.1,max_delay=0.1):
    """Should be called at the very beginning of a script."""
    global dt
    dt = timestep
    initDocument('','')

def end():
    PrettyPrint(xmldoc)

def run(simtime):
    PrettyPrint(xmldoc)

def setRNGseeds(seedList):
    """Globally set rng seeds."""
    raise "Not yet implemented"
    

# ==============================================================================
#   Low-level API for creating, connecting and recording from individual neurons
# ==============================================================================

def create(celltype,paramDict=None,n=1):
    """
    Create n cells all of the same type.
    If n > 1, return a list of cell ids/references.
    If n==1, return just the single id.
    """
    global gid, gidlist, nhost, myid
    
    assert n > 0, 'n must be a positive integer'
    #must look if the cellclass is not already defined
    
    if isinstance(cellclass, type):
        celltype = cellclass(paramDict)
    elif isinstance(cellclass,str):
        #define a new cellType
        celltype = FacetsmlCellType(cellclass,paramDict)
 
    # round-robin partitioning
    newgidlist = [i+myid for i in range(gid,gid+n,nhost) if i < gid+n-myid]
    for cell_id in newgidlist:
        celltype.domNode.setAttribute("name",'cell%d' % cell_id)
    
    gidlist.extend(newgidlist)
    cell_list = range(gid,gid+n)
    gid = gid+n
    if n == 1:
        cell_list = cell_list[0]
    return cell_list

def connect(source,target,weight=None,delay=None,synapse_type=None,p=1,rng=None):
    """Connect a source of spikes to a synaptic target. source and target can
    both be individual cells or lists of cells, in which case all possible
    connections are made with probability p, using either the random number
    generator supplied, or the default rng otherwise.
    Weights should be in nA or uS."""
    raise Exception("Method not yet implemented")


def set(cells,cellclass,param,val=None):
    """Set one or more parameters of an individual cell or list of cells.
    param can be a dict, in which case val should not be supplied, or a string
    giving the parameter name, in which case val is the parameter value.
    cellclass must be supplied for doing translation of parameter names."""
    raise Exception("Method not yet implemented")


# ==============================================================================
#   High-level API for creating, connecting and recording from populations of
#   neurons.
# ==============================================================================

class Population(common.Population):
    """
    An array of neurons all of the same type. `Population' is used as a generic
    term intended to include layers, columns, nuclei, etc., of cells.
    All cells have both an address (a tuple) and an id (an integer). If p is a
    Population object, the address and id can be inter-converted using :
    id = p[address]
    address = p.locate(id)
    """
    nPop = 0
    
    def __init__(self,dims,cellclass,cellparams=None,label=None):
        """
        dims should be a tuple containing the population dimensions, or a single
          integer, for a one-dimensional population.
          e.g., (10,10) will create a two-dimensional population of size 10x10.
        cellclass should either be a standardized cell class (a class inheriting
        from common.StandardCellType) or a string giving the name of the
        simulator-specific model that makes up the population.
        cellparams should be a dict which is passed to the neuron model
          constructor
        label is an optional name for the population.
        """
        global gid, myid, nhost, gidlist, fullgidlist
        
        common.Population.__init__(self,dims,cellclass,cellparams,label)
        #if self.ndim > 1:
        #    for i in range(1,self.ndim):
        #        if self.dim[i] != self.dim[0]:
        #            raise common.InvalidDimensionsError, "All dimensions must be the same size (temporary restriction)."

        # set the steps list, used by the __getitem__() method.
        self.steps = [1]*self.ndim
        for i in xrange(self.ndim-1):
            for j in range(i+1,self.ndim):
                self.steps[i] *= self.dim[j]

        if isinstance(cellclass, type):
            #maybe we should look if the cellclass is not already defined
            self.celltype = cellclass(cellparams)
            self.cellparams = self.celltype.parameters
            #not used ?
            facetsml_name = self.celltype.facetsml_name
        elif isinstance(cellclass, str): # not a standard model
            #define a new cellType
            self.celltype = FacetsmlCellType(cellclass,paramDict)
        
        
        if not self.label:
            self.label = 'population%d' % Population.nPop
        
        
        #the <population> markup is linked, in NeuroML, to a <cell> markup, which defines the type of cells of the population
        # the cell_type name which makes the link is here the concatenation of 'cell_type_' and population label
        cell_type_label = 'cell_type_%s' % label
        self.celltype.facetsmlCellType.domNode.setAttribute("name",'cell_type_%s' % label)
        
        
        # Now the gid and cellclass are stored as instance of the ID class, which will allow a syntax like
        # p[i,j].set(param, val). But we have also to deal with positions : a population needs to know ALL the positions
        # of its cells, and not only those of the cells located on a particular node (i.e in self.gidlist). So
        # each population should store what we call a "fullgidlist" with the ID of all the cells in the populations 
        # (and therefore their positions)
        #self.fullgidlist = [ID(i) for i in range(gid, gid+self.size) if i < gid+self.size]
        
        # self.gidlist is now derived from self.fullgidlist since it contains only the cells of the population located on
        # the node
        #self.gidlist     = [self.fullgidlist[i+myid] for i in range(0, len(self.fullgidlist),nhost) if i < len(self.fullgidlist)-myid]
        #self.gid_start   = gid

        
            
        populationsNode = initDocument('http://morphml.org/networkml/schema','populations','net')
    
        populationNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','net:population')
        populationNode.setAttribute('name',label)
        populationsNode.appendChild(populationNode)
        self.dom_node = populationNode
    
        cell_typeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','net:cell_type')
        cell_typeTextNode = xmldoc.createTextNode(cell_type_label)
        cell_typeNode.appendChild(cell_typeTextNode)
        populationNode.appendChild(cell_typeNode)
        
        
            
        """
        the minimal neuroml to add there is :
        <net:pop_location reference="aReference">
            <net:grid_arrangement>
                <net:rectangular_location name="aName">
                    <meta:corner x="0" y="0" z="0"/>
                    <meta:size depth="10" height="100" width="100"/>
                </net:rectangular_location>
                <net:spacing x="10" y="10" z="10"/>
            </net:grid_arrangement>
        </net:pop_location>
        """
        pop_locationNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','net:pop_location')
        pop_locationNode.setAttribute('reference','aReference')
        populationNode.appendChild(pop_locationNode)
        
        grid_arrangementNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','net:grid_arrangement')
        pop_locationNode.appendChild(grid_arrangementNode)
        
        rectangular_locationNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','net:rectangular_location')
        rectangular_locationNode.setAttribute('name','aName')
        grid_arrangementNode.appendChild(rectangular_locationNode)
        
        cornerNode = xmldoc.createElementNS('http://morphml.org/metadata/schema','meta:corner')
        cornerNode.setAttribute('x','0')
        cornerNode.setAttribute('y','0')
        cornerNode.setAttribute('z','0')
        rectangular_locationNode.appendChild(cornerNode)
        
        sizeNode = xmldoc.createElementNS('http://morphml.org/metadata/schema','meta:size')
        #neuroml is always in 3D, adding 0 for non covered dimensions
        sizeNode.setAttribute('depth',str(10*dims[0]))
        sizeNode.setAttribute('height',str(10*dims[1]))
        if(dims.__len__() > 2):
            sizeNode.setAttribute('width',str(10*dims[2]))
        else:
            sizeNode.setAttribute('width','0')
        rectangular_locationNode.appendChild(sizeNode)
        
        spacingNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','net:spacing')
        spacingNode.setAttribute('x','10')
        spacingNode.setAttribute('y','10')
        spacingNode.setAttribute('z','10')
        grid_arrangementNode.appendChild(spacingNode)
        
    
        Population.nPop += 1
        gid = gid+self.size

        # We add the gidlist of the population to the global gidlist
        #gidlist += self.gidlist
        
        # By default, the positions of the cells are their coordinates, given by the locate()
        # method. Note that each node needs to know all the positions of all the cells 
        # in the population
        #for cell_id in self.fullgidlist:
        #    cell_id.setCellClass(cellclass)
        #    cell_id.setPosition(self.locate(cell_id))
                    
        
        PrettyPrint(xmldoc)

        
    def __getitem__(self,addr):
        """Returns a representation of the cell with coordinates given by addr,
           suitable for being passed to other methods that require a cell id.
           Note that __getitem__ is called when using [] access, e.g.
             p = Population(...)
             p[2,3] is equivalent to p.__getitem__((2,3)).
        """

        global gidlist

        # What we actually pass around are gids.
        if isinstance(addr,int):
            addr = (addr,)
        if len(addr) != len(self.dim):
            raise common.InvalidDimensionsError, "Population has %d dimensions. Address was %s" % (self.ndim,str(addr))
        index = 0
        for i,s in zip(addr,self.steps):
            index += i*s
        id = index + self.gid_start
        assert addr == self.locate(id), 'index=%s addr=%s id=%s locate(id)=%s' % (index, addr, id, self.locate(id))
        # We return the gid as an ID object. Note that each instance of Populations
        # distributed on several node can give the ID object, because fullgidlist is duplicated
        # and common to all the node (not the case of global gidlist, or self.gidlist)
        return self.fullgidlist[index]

        
    def locate(self,id):
        """Given an element id in a Population, return the coordinates.
               e.g. for  4 6  , element 2 has coordinates (1,0) and value 7
                         7 9
        """
        # id should be a gid
        assert isinstance(id,int), "id is %s, not int" % type(id)
        id -= self.gid_start
        if self.ndim == 3:
            rows = self.dim[1]; cols = self.dim[2]
            i = id/(rows*cols); remainder = id%(rows*cols)
            j = remainder/cols; k = remainder%cols
            coords = (i,j,k)
        elif self.ndim == 2:
            cols = self.dim[1]
            i = id/cols; j = id%cols
            coords = (i,j)
        elif self.ndim == 1:
            coords = (id,)
        else:
            raise common.InvalidDimensionsError
        return coords
        
        
    def set(self,param,val=None):
        """
        Set one or more parameters for every cell in the population. param
        can be a dict, in which case val should not be supplied, or a string
        giving the parameter name, in which case val is the parameter value.
        val can be a numeric value, or list of such (e.g. for setting spike times).
        e.g. p.set("tau_m",20.0).
             p.set({'tau_m':20,'v_rest':-65})
        """
        paramDict = checkParams(param,val)

        for param,val in paramDict.items():
            if isinstance(val,str):
                #I have to retrieve the <cell> markup which defines the type of cells of that population
                # self.cellType is the cellType class, which contains the corresponding domNode
                # self.cellType.facetsml_name, for example "IF_curr_alpha" is the name of the markup under <cell>
                cellTypeNode = self.cellType.domNode.getElementsByTagNameNS('http://morphml.org/neuroml/schema',self.celltype.facetsml_name)
                cellTypeNode.setAttribute(param,val)


        
    def tset(self,parametername,valueArray):
        """
        'Topographic' set. Sets the value of parametername to the values in
        valueArray, which must have the same dimensions as the Population.
        """
        raise Exception("not yet implemented")
    
    def rset(self,parametername,rand_distr):
        """
        'Random' set. Sets the value of parametername to a value taken from
        rand_distr, which should be a RandomDistribution object.
        """
        raise Exception("not yet implemented")


    def randomInit(self,rand_distr):
        """
        Sets initial membrane potentials for all the cells in the population to
        random values.
        """
        raise Exception("not yet implemented")
    

    
class Projection(common.Projection):
    """
    A container for all the connections of a given type (same synapse type and
    plasticity mechanisms) between two populations, together with methods to set
    parameters of those connections, including of plasticity mechanisms.
    """
    
    def __init__(self,presynaptic_population,postsynaptic_population,method='allToAll',methodParameters=None,source=None,target=None,label=None,rng=None):
        """
        presynaptic_population and postsynaptic_population - Population objects.
        
        source - string specifying which attribute of the presynaptic cell signals action potentials
        
        target - string specifying which synapse on the postsynaptic cell to connect to
        If source and/or target are not given, default values are used.
        
        method - string indicating which algorithm to use in determining connections.
        Allowed methods are 'allToAll', 'oneToOne', 'fixedProbability',
        'distanceDependentProbability', 'fixedNumberPre', 'fixedNumberPost',
        'fromFile', 'fromList'
        
        methodParameters - dict containing parameters needed by the connection method,
        although we should allow this to be a number or string if there is only
        one parameter.
        
        rng - since most of the connection methods need uniform random numbers,
        it is probably more convenient to specify a Random object here rather
        than within methodParameters, particularly since some methods also use
        random numbers to give variability in the number of connections per cell.
        
        
        
        
        example of NeuroML for projections :
        <projections units="Physiological Units" xmlns="http://morphml.org/networkml/schema">
           <projection name="NetworkConnection">
               <source>CellGroupA</source>
               <target>CellGroupB</target>
               <synapse_props>
                   <synapse_type>DoubExpSynA</synapse_type>
                   <default_values internal_delay="5" weight="1" threshold="-20"/>
               </synapse_props>
               <connections>
                   <connection id="0">
                       <pre cell_id="0" segment_id = "0" fraction_along="0.5"/>
                       <post cell_id="1" segment_id = "1"/>
                   </connection>
                   <connection id="1">
                       <pre cell_id="2" segment_id = "0"/>
                       <post cell_id="1" segment_id = "0"/>
                   </connection>
                   <connection id="1">
                       <pre cell_id="3" segment_id = "0"/>
                       <post cell_id="1" segment_id = "1"/>
                       <properties internal_delay="10" weight="0.5"/>                    <!-- adjusted value -->
                   </connection>
               </connections>
           </projection>
           <projection name="2">
               <source>CellGroupA</source>
               <target>CellGroupB</target>
               <synapse_props>
                   <synapse_type>DoubExpSynA</synapse_type>
                   <default_values/>
               </synapse_props>
               <connectivity_pattern>
                   <all_to_all/>
               </connectivity_pattern>
           </projection>
       </projections>
        """
        common.Projection.__init__(self,presynaptic_population,postsynaptic_population,method,methodParameters,source,target,label,rng)
        self.connection = []
        self._targets = []
        self._sources = []
        
        projectionsNode = initDocument('http://morphml.org/networkml/schema','projections')
        projectionsNode.setAttribute('units','Physiological Units')
        
        projectionNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','projection')
        projectionNode.setAttribute('name',label)
        projectionsNode.appendChild(projectionNode)
        self.domNode = projectionNode
        
        sourceNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','source')
        
        #evaluating presynaptic_populationName
        if isinstance(presynaptic_population, Population):
            presynaptic_populationName = presynaptic_population.label
        elif isinstance(presynaptic_population, str):
            presynaptic_populationName = presynaptic_population
        
        
        sourceTextNode = xmldoc.createTextNode(presynaptic_populationName)
        sourceNode.appendChild(sourceTextNode)
        projectionNode.appendChild(sourceNode)
        
        targetNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','target')
        
        #evaluating postsynaptic_populationName
        if isinstance(postsynaptic_population, Population):
            postsynaptic_populationName = postsynaptic_population.label
        elif isinstance(postsynaptic_population, str):
            postsynaptic_populationName = postsynaptic_population
        
        targetTextNode = xmldoc.createTextNode(postsynaptic_populationName)
        targetNode.appendChild(targetTextNode)
        projectionNode.appendChild(targetNode)
        
        connection_method = getattr(self,'_%s' % method)
        
        projectionNode.appendChild(connection_method(methodParameters))
        
        PrettyPrint(xmldoc)
        
    
    
    # --- Connection methods ---------------------------------------------------
    
    
    def __connect(self,synapse_type,):
        """
        Here this function doesn't have the same meaning than in neuron.py, it just creates the
        neuroML template around the connectivity_pattern
        """
        """
         <projection name="2">
            <source>CellGroupA</source>
            <target>CellGroupB</target>
            <synapse_props>
                <synapse_type>DoubExpSynA</synapse_type>
                <default_values/>
            </synapse_props>
            <connectivity_pattern>
                <all_to_all/>
            </connectivity_pattern>
        </projection>
        """
        
        synapse_propsNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','synapse_props')
        projectionNode = self.domNode
        
        synapse_typeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','synapse_type')
        synapse_typeTextNode = xmldoc.createTextNode(synapse_type)
        synapse_typeNode.appendChild(synapse_typeTextNode)
        synapse_propsNode.appendChild(synapse_typeNode)
        
        default_valuesNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','default_values')
        synapse_propsNode.appendChild(default_valuesNode)
        projectionNode.appendChild(synapse_propsNode)
    
    
    def _allToAll(self,parameters=None,synapse_type=None):
        """
        Connect all cells in the presynaptic population to all cells in the
        postsynaptic population.
        """
        """
        <connectivity_pattern>
            <all_to_all/>
        </connectivity_pattern>
        """
        
        #still have to create the connectivity_pattern node which will be created by its corresponding method
        __connect(self,parameters,synapse_type)
        connectivity_patternNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connectivity_pattern')
        
        connectivity_patternTypeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','all_to_all')
        connectivity_patternNode.appendChild(connectivity_patternTypeNode)
        
        return connectivity_patternNode
    
        
    def _oneToOne(self,synapse_type=None):
        """
        Where the pre- and postsynaptic populations have the same size, connect
        cell i in the presynaptic population to cell i in the postsynaptic
        population for all i.
        In fact, despite the name, this should probably be generalised to the
        case where the pre and post populations have different dimensions, e.g.,
        cell i in a 1D pre population of size n should connect to all cells
        in row i of a 2D post population of size (n,m).
        """
        __connect(self,parameters,synapse_type)
        connectivity_patternNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connectivity_pattern')
        
        connectivity_patternTypeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','one_to_one')
        connectivity_patternNode.appendChild(connectivity_patternTypeNode)
        
        return connectivity_patternNode

    
    def _fixedProbability(self,parameters,synapse_type=None):
        """
        For each pair of pre-post cells, the connection probability is constant.
        """
        allow_self_connections = True
        try:
            p_connect = float(parameters)
        except TypeError:
            p_connect = parameters['p_connect']
            if parameters.has_key('allow_self_connections'):
                allow_self_connections = parameters['allow_self_connections']

        __connect(self,parameters,synapse_type)
        connectivity_patternNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connectivity_pattern')
        
        connectivity_patternTypeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','fixed_probability')
        connectivity_patternTypeNode.setAttribute('probability',p_connect)
        connectivity_patternNode.appendChild(connectivity_patternTypeNode)
        
        return connectivity_patternNode


    def _distanceDependentProbability(self,parameters,synapse_type=None):
        """
        For each pair of pre-post cells, the connection probability depends on distance.
        d_expression should be the right-hand side of a valid python expression
        for probability, involving 'd', e.g. "exp(-abs(d))", or "float(d<3)"
        """
        raise Exception("Method not yet implemented")
        

    def _fixedNumberPre(self,parameters,synapse_type=None):
        """Each presynaptic cell makes a fixed number of connections."""
        """
        <connectivity_pattern>
           <per_cell_connection num_per_source="1.2" max_per_target="2.3" direction="PreToPost"/>
        </connectivity_pattern>
        """
        self.synapse_type = synapse_type
        allow_self_connections = True
        if type(parameters) == types.IntType:
            n = parameters
            assert n > 0
            fixed = True
        elif type(parameters) == types.DictType:
            if parameters.has_key('n'): # all cells have same number of connections
                n = int(parameters['n'])
                assert n > 0
                fixed = True
            elif parameters.has_key('rand_distr'): # number of connections per cell follows a distribution
                rand_distr = parameters['rand_distr']
                assert isinstance(rand_distr,RandomDistribution)
                fixed = False
            if parameters.has_key('allow_self_connections'):
                allow_self_connections = parameters['allow_self_connections']
        elif isinstance(parameters, RandomDistribution):
            rand_distr = parameters
            fixed = False
        else:
            raise Exception("Invalid argument type: should be an integer, dictionary or RandomDistribution object.")
                
        __connect(self,parameters,synapse_type)
        connectivity_patternNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connectivity_pattern')
        
        connectivity_patternTypeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','per_cell_connection')
        connectivity_patternTypeNode.setAttribute('num_per_source',n)
        connectivity_patternTypeNode.setAttribute('max_per_target',n)
        connectivity_patternTypeNode.setAttribute('direction','PreToPost')
        connectivity_patternNode.appendChild(connectivity_patternTypeNode)
        
        return connectivity_patternNode
    
            
    def _fixedNumberPost(self,parameters,synapse_type=None):
        """Each postsynaptic cell receives a fixed number of connections."""
        """
        <connectivity_pattern>
           <per_cell_connection num_per_source="1.2" max_per_target="2.3" direction="PostToPre"/>
        </connectivity_pattern>
        """
        self.synapse_type = synapse_type
        allow_self_connections = True
        if type(parameters) == types.IntType:
            n = parameters
            assert n > 0
            fixed = True
        elif type(parameters) == types.DictType:
            if parameters.has_key('n'): # all cells have same number of connections
                n = int(parameters['n'])
                assert n > 0
                fixed = True
            elif parameters.has_key('rand_distr'): # number of connections per cell follows a distribution
                rand_distr = parameters['rand_distr']
                assert isinstance(rand_distr,RandomDistribution)
                fixed = False
            if parameters.has_key('allow_self_connections'):
                allow_self_connections = parameters['allow_self_connections']
        elif isinstance(parameters, RandomDistribution):
            rand_distr = parameters
            fixed = False
        else:
            raise Exception("Invalid argument type: should be an integer, dictionary or RandomDistribution object.")
                
        __connect(self,parameters,synapse_type)
        connectivity_patternNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connectivity_pattern')
        
        connectivity_patternTypeNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','per_cell_connection')
        connectivity_patternTypeNode.setAttribute('num_per_source',n)
        connectivity_patternTypeNode.setAttribute('max_per_target',n)
        connectivity_patternTypeNode.setAttribute('direction','PostToPre')
        connectivity_patternNode.appendChild(connectivity_patternTypeNode)
        
        return connectivity_patternNode



    def _fromFile(self,parameters,synapse_type=None):
        """
        Load connections from a file.
        """
        lines =[]
        if type(parameters) == types.FileType:
            fileobj = parameters
            # should check here that fileobj is already open for reading
            lines = fileobj.readlines()
        elif type(parameters) == types.StringType:
            filename = parameters
            # now open the file...
            f = open(filename,'r')
            lines = f.readlines()
        elif type(parameters) == types.DictType:
            # dict could have 'filename' key or 'file' key
            # implement this...
            raise "Argument type not yet implemented"
        
        # We read the file and gather all the data in a list of tuples (one per line)
        input_tuples = []
        for line in lines:
            single_line = line.rstrip()
            single_line = single_line.split("\t", 4)
            input_tuples.append(single_line)    
        f.close()
        
        return self._fromList(input_tuples, synapse_type)
    
    def _fromList(self,conn_list,synapse_type=None):
        """
        Read connections from a list of tuples,
        containing ['src[x,y]', 'tgt[x,y]', 'weight', 'delay']
        """
        """
        <projection name="NetworkConnection">
            <source>CellGroupA</source>
            <target>CellGroupB</target>
            <synapse_props>
                <synapse_type>DoubExpSynA</synapse_type>
                <default_values internal_delay="5" weight="1" threshold="-20"/>
            </synapse_props>
            <connections>
                <connection id="1">
                    <pre cell_id="3" segment_id = "0"/>
                    <post cell_id="1" segment_id = "1"/>
                    <properties internal_delay="10" weight="0.5"/>                    <!-- adjusted value -->
                </connection>
            </connections>
        </projection>
        """
        __connect(self,synapse_type)
        projectionNode = self.domNode
        connectionsNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connections')
        projectionNode.appendChild(connectionsNode)
        
        # Then we go through those tuple and extract the fields
        for i in xrange(len(conn_list)):
            src    = conn_list[i][0]
            tgt    = conn_list[i][1]
            weight = eval(conn_list[i][2])
            delay  = eval(conn_list[i][3])
            src = "[%s" %src.split("[",1)[1]
            tgt = "[%s" %tgt.split("[",1)[1]
            src  = eval("self.pre%s" % src)
            tgt  = eval("self.post%s" % tgt)
            
            connectionNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','connection')
            connectionNode.setAttribute('id',i)
            preNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','pre')
            preNode.setAttribute('cell_id',src)
            connectionNode.appendChild(preNode)
            
            postNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','post')
            postNode.setAttribute('cell_id',tgt)
            connectionNode.appendChild(postNode)
            
            propertiesNode = xmldoc.createElementNS('http://morphml.org/networkml/schema','properties')
            propertiesNode.setAttribute('internal_delay',delay)
            propertiesNode.setAttribute('weight',weight)
            connectionNode.appendChild(propertiesNode)
            connectionsNode.appendChild(connectionNode)
            
        
        return connectivity_patternNode
        
    
    # --- Methods for setting connection parameters ----------------------------
    
    def setWeights(self,w):
        """
        w can be a single number, in which case all weights are set to this
        value, or a list/1D array of length equal to the number of connections
        in the population.
        Weights should be in nA for current-based and µS for conductance-based
        synapses.
        """
        raise Exception("Method not yet implemented")


    def randomizeWeights(self,rand_distr):
        """
        Set weights to random values taken from rand_distr.
        """
        # If we have a native rng, we do the loops in hoc. Otherwise, we do the loops in
        # Python
        raise Exception("Method not yet implemented")
        
        
    
    def setDelays(self,d):
        """
        d can be a single number, in which case all delays are set to this
        value, or an array with the same dimensions as the Projection array.
        """
        raise Exception("Method not yet implemented")

        
    def randomizeDelays(self,rand_distr):
        """
        Set delays to random values taken from rand_distr.
        """   
        # If we have a native rng, we do the loops in hoc. Otherwise, we do the loops in
        # Python  
        raise Exception("Method not yet implemented")

        
    def setTopographicDelays(self,delay_rule,rand_distr=None):
        """
        Set delays according to a connection rule expressed in delay_rule, based
        on the delay distance 'd' and an (optional) rng 'rng'. For example,
        the rule can be "rng*d + 0.5", with "a" extracted from the rng and
        d being the distance.
        """
        raise Exception("Method not yet implemented")
        
    def setThreshold(self,threshold):
        """
        Where the emission of a spike is determined by watching for a
        threshold crossing, set the value of this threshold.
        """
        # This is a bit tricky, because in NEST the spike threshold is a
        # property of the cell model, whereas in NEURON it is a property of the
        # connection (NetCon).
        raise Exception("Method not yet implemented")
    
    # --- Methods relating to synaptic plasticity ------------------------------
    
    def setupSTDP(self,stdp_model,parameterDict):
        """Set-up STDP."""
        
        # Define the objref to handle plasticity
        raise Exception("Method not yet implemented")
    
    def toggleSTDP(self,onoff):
        """Turn plasticity on or off. 
        onoff = True => ON  and onoff = False => OFF. By defaut, it is on."""
        # We do the loop in hoc, to speed up the code
        raise Exception("Method not yet implemented")
        
    
    def setMaxWeight(self,wmax):
        """Note that not all STDP models have maximum or minimum weights."""
        # We do the loop in hoc, to speed up the code
        raise Exception("Method not yet implemented")

    
    def setMinWeight(self,wmin):
        """Note that not all STDP models have maximum or minimum weights."""
        # We do the loop in hoc, to speed up the code
        raise Exception("Method not yet implemented")
    
    
    # --- Methods for writing/reading information to/from file. ----------------
    
    def saveConnections(self,filename,gather=False):
        """Save connections to file in a format suitable for reading in with the
        'fromFile' method."""
        raise Exception("Method not yet implemented")
    
    def printWeights(self,filename,format=None,gather=True):
        """Print synaptic weights to file."""
        raise Exception("Method not yet implemented")


    def weightHistogram(self,min=None,max=None,nbins=10):
        """
        Return a histogram of synaptic weights.
        If min and max are not given, the minimum and maximum weights are
        calculated automatically.
        """
        # it is arguable whether functions operating on the set of weights
        # should be put here or in an external module.
        raise Exception("Method not yet implemented")

 
# ==============================================================================
#   Utility classes
# ==============================================================================
   
Timer = common.Timer  # not really relevant here except for timing how long it takes
                      # to write the XML file. Needed for API consistency.

# ==============================================================================