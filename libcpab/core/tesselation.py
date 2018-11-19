# -*- coding: utf-8 -*-
"""
Created on Sun Nov 18 14:23:25 2018

@author: nsde
"""

#%%
import numpy as np

def make_hashable(arr):
    """ Make an array hasable. In this way we can use built-in functions like
        set(...) and intersection(...) on the array
    """
    return tuple([tuple(r.tolist()) for r in arr])

#%%
class Tesselation:
    """ Base tesselation class. This function is not meant to be called,
        but descripes the base structure that needs to be implemented in
        1D, 2D, and 3D.
        
    Args:
        nc: list with number of cells
        domain_min: value of the lower bound(s) of the domain
        domain_max: value of the upper bound(s) of the domain
        zero_boundary: bool, if true the velocity is zero on the boundary
        volume_perservation: bool, if true volume is perserved
        
    Methods that should not be implemented in subclasses:
        @get_constrain_matrix:
        @get_cell_centers:
        @create_zero_trace_constrains:
            
    Methods that should be implemented in subclasses:
        @find_verts:
        @find_verts_outside:
        @create_continuity_constrains:
        @create_zero_boundary_constrains:
        
    """
    def __init__(self, nc, domain_min=0, domain_max=1,
                 zero_boundary = True, volume_perservation=False):
        # Save parameters
        self.nc = nc
        self.domain_min = domain_min
        self.domain_max = domain_max
        self.zero_boundary = zero_boundary
        self.volume_perservation = volume_perservation
    
        # Get vertices
        self.find_verts()
        
        # Find shared vertices
        self.find_shared_verts()
        
        # find auxility vertices, if transformation is valid outside
        if not zero_boundary: self.find_verts_outside()
        
        # Get continuity constrains
        self.L = self.create_continuity_constrains()
        
        # If zero boundary, add constrains
        if zero_boundary:
            temp = self.create_zero_boundary_constrains()
            self.L = np.concatenate((self.L, temp), axis=0)
            
        # If volume perservation, add constrains
        if volume_perservation:
            temp = self.create_zero_trace_constrains()
            self.L = np.concatenate((self.L, temp), axis=0)
    
    def get_constrain_matrix(self):
        return self.L
    
    def get_cell_centers(self):
        return np.mean(self.verts[:,:,:self.ndim], axis=1)
    
    def find_verts(self):
        raise NotImplementedError
        
    def find_shared_verts(self):
        # Iterate over all pairs of cell to find cells with intersecting cells
        shared_v, shared_v_idx = [ ], [ ]
        for i in range(self.nC):
            for j in range(self.nC):
                vi = make_hashable(self.verts[i])
                vj = make_hashable(self.verts[j])
                shared_verts = set(vi).intersection(vj)
                if len(shared_verts) == self.ndim and (j,i) not in shared_v_idx:
                    shared_v.append(list(shared_verts))
                    shared_v_idx.append((i,j))
        
        # Save result
        self.shared_v = np.asarray(shared_v)
        self.shared_v_idx = shared_v_idx
        
    def find_verts_outside(self):
        raise NotImplementedError
        
    def create_continuity_constrains(self):
        raise NotImplementedError
        
    def create_zero_boundary_constrains(self):
        raise NotImplementedError
        
    def create_zero_trace_constrains(self):
        """ The volume perservation constrains, that corresponds to the trace
            of each matrix being 0. These can be written general for all dims."""
        Ltemp = np.zeros((self.nC, self.n_params*self.nC))
        row = np.concatenate((np.eye(self.ndim), np.zeros((self.ndim, 1))), axis=1).flatten()
        for c in range(self.nC):
            Ltemp[c,self.n_params*c:self.n_params*(c+1)] = row
        return Ltemp
        
#%%
class Tesselation1D(Tesselation):
    def __init__(self, nc, domain_min=0, domain_max=1,
                 zero_boundary = True, volume_perservation=False):
        # 1D parameters
        self.n_params = 2
        self.nC = np.prod(nc)
        self.ndim = 1
        
        # Initialize super class
        super(Tesselation1D, self).__init__(nc, domain_min, domain_max,
             zero_boundary, volume_perservation)
        
    def find_verts(self):
        Vx = np.linspace(self.domain_min[0], self.domain_max[0], self.nc[0]+1)
        
        # Find cell index and verts for each cell
        cells, verts = [ ], [ ]
        for i in range(self.nc[0]):
            v1 = tuple([Vx[i], 1])
            v2 = tuple([Vx[i+1], 1])
            verts.append((v1, v2))
            cells.append((i))
        
        # Convert to array
        self.verts = np.asarray(verts)
        self.cells = cells
        
    def find_verts_outside(self):
        pass # in 1D, we do not need auxilliry points
    
    def create_continuity_constrains(self):
        Ltemp = np.zeros(shape=(self.nC-1,2*self.nC))
        for idx, v in enumerate(self.shared_v):
            Ltemp[idx,2*idx:2*(idx+2)] = [*v[0], *(-v[0])]
        return Ltemp
        
    def create_zero_boundary_constrains(self):
        Ltemp = np.zeros((2,2*self.nC))
        Ltemp[0,:2] = [self.domain_min[0], 1]
        Ltemp[1,-2:] = [self.domain_max[0], 1]
        return Ltemp

#%%
class Tesselation2D(Tesselation):
    def __init__(self, nc, domain_min=0, domain_max=1,
                 zero_boundary = True, volume_perservation=False):
        # 1D parameters
        self.n_params = 6 
        self.nC = 4*np.prod(nc) # 4 triangle per cell
        self.ndim = 2
        
        # Initialize super class
        super(Tesselation2D, self).__init__(nc, domain_min, domain_max,
             zero_boundary, volume_perservation)
    
    def find_verts(self):
        Vx = np.linspace(self.domain_min[0], self.domain_max[0], self.nc[0]+1)
        Vy = np.linspace(self.domain_min[1], self.domain_max[1], self.nc[1]+1)
        
        # Find cell index and verts for each cell
        cells, verts = [ ], [ ]
        for i in range(self.nc[1]):
            for j in range(self.nc[0]):
                ul = tuple([Vx[j],Vy[i],1])
                ur = tuple([Vx[j+1],Vy[i],1])
                ll = tuple([Vx[j],Vy[i+1],1])
                lr = tuple([Vx[j+1],Vy[i+1],1])
                
                center = [(Vx[j]+Vx[j+1])/2,(Vy[i]+Vy[i+1])/2,1]
                center = tuple(center)                 
                
                verts.append((center,ul,ur))  # order matters!
                verts.append((center,ur,lr))  # order matters!
                verts.append((center,lr,ll))  # order matters!
                verts.append((center,ll,ul))  # order matters!                
        
                cells.append((j,i,0))
                cells.append((j,i,1))
                cells.append((j,i,2))
                cells.append((j,i,3))
                
        # Convert to array
        self.verts = np.asarray(verts)
        self.cells = cells
        
    def find_verts_outside(self):
        shared_v, shared_v_idx = [ ], [ ]
        
        left =   np.zeros((self.nC, self.nC), np.bool)    
        right =  np.zeros((self.nC, self.nC), np.bool) 
        top =    np.zeros((self.nC, self.nC), np.bool) 
        bottom = np.zeros((self.nC, self.nC), np.bool) 
        
        for i in range(self.nC):
            for j in range(self.nC):
                
                vi = make_hashable(self.verts[i])
                vj = make_hashable(self.verts[j])
                shared_verts = set(vi).intersection(vj)
                
                mi = self.cells[i]
                mj = self.cells[j]
        
                # leftmost col, left triangle, adjacent rows
                if  mi[0]==mj[0]==0 and \
                    mi[2]==mj[2]==3 and \
                    np.abs(mi[1]-mj[1])==1: 
                        
                    left[i,j]=True
                
                # rightmost col, right triangle, adjacent rows                 
                if  mi[0]==mj[0]==self.nc[0]-1 and \
                    mi[2]==mj[2]==1 and \
                    np.abs(mi[1]-mj[1])==1: 
        
                    right[i,j]=True
                
                # uppermost row, upper triangle , adjacent cols                    
                if  mi[1]==mj[1]==0 and \
                    mi[2]==mj[2]==0 and \
                    np.abs(mi[0]-mj[0])==1:
                        
                    top[i,j]=True
                
                # lowermost row, # lower triangle, # adjacent cols            
                if  mi[1]==mj[1]==self.nc[1]-1 and \
                    mi[2]==mj[2]==2 and \
                    np.abs(mi[0]-mj[0])==1:
                        
                    bottom[i,j]=True
                                
                if  len(shared_verts) == 1 and \
                    any([left[i,j],right[i,j],top[i,j],bottom[i,j]]) and \
                    (j,i) not in shared_v_idx:
                        
                    v_aux = list(shared_verts)[0] # v_aux is a tuple
                    v_aux = list(v_aux) # Now v_aux is a list (i.e. mutable)
                    if left[i,j] or right[i,j]:
                        v_aux[0]-=10 # Create a new vertex  with the same y
                    elif top[i,j] or bottom[i,j]:
                        v_aux[1]-=10 # Create a new vertex  with the same x
                    else:
                        raise ValueError("WTF?")                        
                    shared_verts = [tuple(shared_verts)[0], tuple(v_aux)]
                    shared_v.append(shared_verts)
                    shared_v_idx.append((i,j))
        
        # Concat to the current list of vertices
        self.shared_v = np.concatenate((self.shared_v, shared_v))
        self.shared_v_idx = np.concatenate((self.shared_v_idx, shared_v_idx))

    def create_continuity_constrains(self):
        Ltemp = np.zeros(shape=(0,6*self.nC))
        count = 0
        for i,j in self.shared_v_idx:
    
            # Row 1 [x_a^T 0_{1x3} -x_a^T 0_{1x3}]
            row1 = np.zeros(shape=(6*self.nC))
            row1[(6*i):(6*(i+1))] = np.append(np.array(self.shared_v[count][0]), 
                                              np.zeros((1,3)))
            row1[(6*j):(6*(j+1))] = np.append(-np.array(self.shared_v[count][0]), 
                                              np.zeros((1,3)))
            
            # Row 2 [0_{1x3} x_a^T 0_{1x3} -x_a^T]
            row2 = np.zeros(shape=(6*self.nC))
            row2[(6*i):(6*(i+1))] = np.append(np.zeros((1,3)), 
                                              np.array(self.shared_v[count][0]))
            row2[(6*j):(6*(j+1))] = np.append(np.zeros((1,3)), 
                                              -np.array(self.shared_v[count][0]))
            
            # Row 3 [x_b^T 0_{1x3} -x_b^T 0_{1x3}]
            row3 = np.zeros(shape=(6*self.nC))
            row3[(6*i):(6*(i+1))] = np.append(np.array(self.shared_v[count][1]), 
                                              np.zeros((1,3)))
            row3[(6*j):(6*(j+1))] = np.append(-np.array(self.shared_v[count][1]), 
                                              np.zeros((1,3)))
            
            # Row 4 [0_{1x3} x_b^T 0_{1x3} -x_b^T]
            row4 = np.zeros(shape=(6*self.nC))
            row4[(6*i):(6*(i+1))] = np.append(np.zeros((1,3)), 
                                              np.array(self.shared_v[count][1]))
            row4[(6*j):(6*(j+1))] = np.append(np.zeros((1,3)), 
                                              -np.array(self.shared_v[count][1]))
                        
            Ltemp = np.vstack((Ltemp, row1, row2, row3, row4))
            
            count += 1
        
        return Ltemp
        
    def create_zero_boundary_constrains(self):
        xmin, ymin = self.domain_min
        xmax, ymax = self.domain_max
        Ltemp = np.zeros(shape=(0,6*self.nC))
        for c in range(self.nC):
            for v in self.verts[c]:
                if(v[0] == xmin or v[0] == xmax): 
                    row = np.zeros(shape=(6*self.nC))
                    row[(6*c):(6*(c+1))] = np.append(np.zeros((1,3)),v)
                    Ltemp = np.vstack((Ltemp, row))
                if(v[1] == ymin or v[1] == ymax): 
                    row = np.zeros(shape=(6*self.nC))
                    row[(6*c):(6*(c+1))] = np.append(v,np.zeros((1,3)))
                    Ltemp = np.vstack((Ltemp, row))
        return Ltemp

#%%
class Tesselation3D(Tesselation):
    def __init__(self, nc, domain_min=0, domain_max=1,
                 zero_boundary = True, volume_perservation=False):
        # 1D parameters
        self.n_params = 12
        self.nC = 6*np.prod(nc) # 6 triangle per cell
        self.ndim = 3
        
        # Initialize super class
        super(Tesselation3D, self).__init__(nc, domain_min, domain_max,
             zero_boundary, volume_perservation)
    
    def find_verts(self):
        Vx = np.linspace(self.domain_min[0], self.domain_max[0], self.nc[0]+1)
        Vy = np.linspace(self.domain_min[1], self.domain_max[1], self.nc[1]+1)
        Vz = np.linspace(self.domain_min[1], self.domain_max[1], self.nc[1]+1)
        
        # Find cell index and verts for each cell
        cells, verts = [ ], [ ]
        for i in range(self.nc[2]):
            for j in range(self.nc[1]):        
                for k in range(self.nc[0]):
                    cnt = tuple([(Vx[k]+Vx[k+1])/2.0, (Vy[j]+Vy[j+1])/2.0, (Vz[i]+Vz[i+1])/2.0, 1])
                    lnl = tuple([Vx[k], Vy[j], Vz[i], 1])
                    lnu = tuple([Vx[k], Vy[j], Vz[i+1], 1])
                    lfl = tuple([Vx[k], Vy[j+1], Vz[i], 1])
                    lfu = tuple([Vx[k], Vy[j+1], Vz[i+1], 1])
                    rnl = tuple([Vx[k+1], Vy[j], Vz[i], 1])
                    rnu = tuple([Vx[k+1], Vy[j], Vz[i+1], 1])
                    rfl = tuple([Vx[k+1], Vy[j+1], Vz[i], 1])
                    rfu = tuple([Vx[k+1], Vy[j+1], Vz[i+1], 1])
                    
                    verts.append((cnt, lnl, lnu, lfl, lfu))
                    verts.append((cnt, lnl, lnu, rnl, rnu))
                    verts.append((cnt, lnl, lfl, rnl, rnu))
                    verts.append((cnt, rnl, rnu, rfl, rfu))
                    verts.append((cnt, lfl, lfu, rfl, rfu))
                    verts.append((cnt, lnu, lfu, rnu, rfu))

                    cells.append((k,j,i,0))
                    cells.append((k,j,i,1))
                    cells.append((k,j,i,2))
                    cells.append((k,j,i,3))
                    cells.append((k,j,i,4))
                    cells.append((k,j,i,5))
        
        # Convert to array
        self.verts = np.asarray(verts)
        self.cells = cells

    def find_verts_outside(self):
        raise NotImplementedError
        
    def create_continuity_constrains(self):
        Ltemp = np.zeros(shape=(0,self.n_params*self.nC))

        for idx, (i,j) in enumerate(self.shared_v_idx):
            for vidx in range(self.ndim):
                for k in range(self.ndim):
                    index1 = self.n_params*i + k*(self.ndim+1)
                    index2 = self.n_params*j + k*(self.ndim+1)
                    row = np.zeros(shape=(1,self.n_params*self.nC))
                    row[0,index1:index1+(self.ndim+1)] = self.shared_v[idx][vidx]
                    row[0,index2:index2+(self.ndim+1)] = -self.shared_v[idx][vidx]
                    Ltemp = np.vstack((Ltemp, row))
        return Ltemp
    
        
    def create_zero_boundary_constrains(self):
        nx, ny, nz = self.nc
        Ltemp = np.zeros(shape=(2*((nx+1)*(ny+1) + (nx+1)*(nz+1) + (ny+1)*(nz+1)), self.n_params*self.nC))
        # xy-plane
        sr = 0
        for i in [0,nz-1]:
            for j in range(ny+1):
                for k in range(nx+1):
                    c_idx = 6 * ( nx*ny*i + nx*min(j,ny-1) + min(k,nx-1) )
                    c_idx += 2 if i==0 else 3

                    vrt = [ k/nx, j/ny, i/(nz-1) ]

                    Ltemp[sr,c_idx*12:(c_idx+1)*12] = np.matrix(vrt+[0,0,1])
                    sr += 1
        # xz-plane
        for j in [0,ny-1]:
            for i in range(nz+1):
                for k in range(nx+1):
                    c_idx = 6 * ( nx*ny*min(i,nz-1) + nx*j + min(k,nx-1) )
                    c_idx += 1 if j==0 else 4

                    vrt = [ k/nx, j/(ny-1), i/nz ]

                    Ltemp[sr,c_idx*12:(c_idx+1)*12] = np.matrix(vrt+[0,1,0])
                    sr += 1
        # yz-plane
        for k in [0,nx-1]:
            for i in range(nz+1):
                for j in range(ny+1):
                    c_idx = 6 * ( nx*ny*min(i,nz-1) + nx*min(j,ny-1) + k )
                    c_idx += 0 if k==0 else 5
            
                    vrt = [ k/(nx-1), j/ny, i/nz ]

                    Ltemp[sr,c_idx*12:(c_idx+1)*12] = np.matrix(vrt+[1,0,0])
                    sr += 1
                    
        return Ltemp
    
#%%
if __name__ == "__main__":
    tess1 = Tesselation1D([5], [0], [1], zero_boundary=True, volume_perservation=True)
    tess2 = Tesselation2D([2,2], [0,0], [1,1], zero_boundary=False, volume_perservation=True)
    tess3 = Tesselation3D([2,2,2], [0,0,0], [1,1,1], zero_boundary=True, volume_perservation=True)