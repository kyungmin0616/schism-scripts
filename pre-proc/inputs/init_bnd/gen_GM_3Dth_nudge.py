#!/usr/bin/env python3
#create 3D boundary condition/nudging files based on GM data
from pylib import *
close("all")

#------------------------------------------------------------------------------
#input
#------------------------------------------------------------------------------
StartT=datenum(2015,1,1); EndT=datenum(2019,12,31)
grd='../../../grid/08/'
dir_data='/rcfs/projects/mhk_modeling/dataset/CMEMS/HAWAII/'

# bnd control
ibnds=[1]           # select open boundary for *.th.nc, check your boundary information in hgrid.gr3

# nudge info
rlmax=0.20
rnu_day=0.25

ifix=1  #ifix=0: fix GM nan 1st, then interp;  ifix=1: interp 1st, then fixed nan

#parameters to each files
iflags=[1,1,1,1,1,1]                    #if iflag=0: skip generating file 
dts=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0]    #time steps for each file (day)
iLP=[0,0,0,0,0,0];   fc=0.25            #iLP=1: remove tidal signal with cutoff frequency fc (day)
snames=['elev2D.th.nc','TEM_3D.th.nc','SAL_3D.th.nc','uv3D.th.nc','TEM_nu.nc','SAL_nu.nc']
mvars=['elev','temp','salt',['u','v'],'temp','salt']

# CMEMS
svars=['zos','thetao','so',['uo','vo'],'thetao','so']
coor=['longitude','latitude','depth']
reftime=datenum(1950,1,1) 

# HYCOM
#svars=['surf_el','water_temp','salinity',['water_u','water_v'],'water_temp','salinity']
#coor=['lon','lat','depth']
#reftime=datenum(2000,1,1)

#------------------------------------------------------------------------------
#interpolate GM data to boundary
#------------------------------------------------------------------------------
#find all GM files
fnames=array([i for i in os.listdir(dir_data) if i.endswith('.nc')])
mti=array([datenum(*array(i.replace('.','_').split('_')[1:5]).astype('int')) for i in fnames])
fpt=(mti>=(StartT-1))*(mti<(EndT+1)); fnames=fnames[fpt]; mti=mti[fpt]
sind=argsort(mti); mti=mti[sind]; fnames=fnames[sind]

#read grid
if fexist(grd+'/grid.npz'):
   gd=loadz(grd+'/grid.npz').hgrid; vd=loadz(grd+'/grid.npz').vgrid
   gd.x,gd.y=gd.lon,gd.lat
else:
   gd=read_schism_hgrid(grd+'/hgrid.ll'); vd=read_schism_vgrid(grd+'/vgrid.in')
nvrt=vd.nvrt

#for each variables
for n,[sname,svar,mvar,dt,iflag] in enumerate(zip(snames,svars,mvars,dts,iflags)):
    if isinstance(svar,str): svar=[svar]; mvar=[mvar]
    if iflag==0: continue
    print('Making {}'.format(sname))
    #get bnd or nugding nodes
    if sname.endswith('_nu.nc'):
       # generate *_nudge.gr3
       if not os.path.isfile('TEM_nudge.gr3') or os.path.isfile('SAL_nudge.gr3'):
           nudge_coeff = np.zeros(len(gd.x), dtype=float)
           rnu_max = 1.0 / rnu_day / 86400.0
           for ibnd in ibnds:
               dis = abs((gd.x + 1j*gd.y)[:, None] - (gd.x[gd.iobn[ibnd-1]] + 1j*gd.y[gd.iobn[ibnd-1]])[None, :]).min(axis=1)
               tmp = (1-dis/rlmax)*rnu_max; tmp[tmp<0] = 0; tmp[tmp>rnu_max] = rnu_max; fp = tmp>0
               nudge_coeff[fp] = tmp[fp]
           gd.write_hgrid('./TEM_nudge.gr3',value=nudge_coeff)
           gd.write_hgrid('./SAL_nudge.gr3',value=nudge_coeff)

       if sname.startswith('TEM'): gdn=read_schism_hgrid('TEM_nudge.gr3')
       if sname.startswith('SAL'): gdn=read_schism_hgrid('SAL_nudge.gr3')
       bind=nonzero(gdn.dp!=0)[0]; nobn=len(bind)
    else:
       bind=[]; nobn=[]
       for ibnd in ibnds:
           bind.extend(gd.iobn[ibnd-1])
       bind=array(bind); nobn=len(bind)
    #compute node xyz
    lxi0=gd.x[bind]; lyi0=gd.y[bind]; bxy=c_[lxi0,lyi0] #for 2D
    lxi=tile(lxi0,[nvrt,1]).T.ravel(); lyi=tile(lyi0,[nvrt,1]).T.ravel() #for 3D
    if vd.ivcor==2:
        lzi=abs(compute_zcor(vd.sigma,gd.dp[bind],ivcor=2,vd=vd)).ravel()
    else:
        lzi=abs(compute_zcor(vd.sigma[bind],gd.dp[bind])).ravel();
    bxyz=c_[lxi,lyi,lzi]

    #interp in space
    S=zdata(); sdict=S.__dict__
    for i in ['time',*mvar]: sdict[i]=[]
    sx0,sy0,sz0=None,None,None #used for check whether GM files have the same dimensions
    for m,fname in enumerate(fnames):
        C=ReadNC('{}/{}'.format(dir_data,fname),1); print(fname)
        ctime=array(C.variables['time'])/24+reftime 
        sx=array(C.variables[coor[0]][:]); sy=array(C.variables[coor[1]][:]); sz=array(C.variables[coor[2]][:]); nz=len(sz); 
        if sz[0] != 0: sz[0]=0
        if sx.max()>180: # convert lon if lon is 0 ~ 360 deg
            print('Convert [0, 360] to [-180, 180]')
            sx=(sx+180)%360-180; lonidx=argsort(sx); sx=sx[lonidx]
        else:
            lonidx=None
        fpz=lzi>=sz.max(); lzi[fpz]=sz.max()-1e-6

        if not array_equal(sx,sx0)*array_equal(sy,sy0)*array_equal(sz,sz0):
            #get interp index for GM data
            if ifix==0:
                sxi,syi=meshgrid(sx,sy); sxy=c_[sxi.ravel(),syi.ravel()];
                cvs=array(C.variables[svars[1]][0]); sindns=[]; sindps=[]
                if lonidx is not None:  cvs=cvs[:,:,lonidx]
                for ii in arange(nz):
                    print('computing GM interpation index: level={}/{}'.format(ii+1,nz))
                    cv=cvs[ii]; ds=cv.shape; cv=cv.ravel()
                    fpn=abs(cv)>1e3; sindn=nonzero(fpn)[0]; sindr=nonzero(~fpn)[0]
                    if len(sindr)!=0: 
                        sindp=sindr[near_pts(sxy[sindn],sxy[sindr])]
                    else:
                        sindp=array([])
                    sindns.append(sindn); sindps.append(sindp)

            #get interp index for pts
            sx0=sx[:]; sy0=sy[:]; sz0=sz[:]; print('get new interp indices: {}'.format(fname))
            idx0=((lxi0[:,None]-sx0[None,:])>=0).sum(axis=1)-1; ratx0=(lxi0-sx0[idx0])/(sx0[idx0+1]-sx0[idx0])
            idy0=((lyi0[:,None]-sy0[None,:])>=0).sum(axis=1)-1; raty0=(lyi0-sy0[idy0])/(sy0[idy0+1]-sy0[idy0])

            idx=((lxi[:,None]-sx0[None,:])>=0).sum(axis=1)-1; ratx=(lxi-sx0[idx])/(sx0[idx+1]-sx0[idx])
            idy=((lyi[:,None]-sy0[None,:])>=0).sum(axis=1)-1; raty=(lyi-sy0[idy])/(sy0[idy+1]-sy0[idy])
            idz=((lzi[:,None]-sz0[None,:])>=0).sum(axis=1)-1; ratz=(lzi-sz0[idz])/(sz0[idz+1]-sz0[idz])

        S.time.extend(ctime)
        for i, cti in enumerate(ctime):
            for k,[svari,mvari] in enumerate(zip(svar,mvar)):
                cv=array(C.variables[svari][i])
                if lonidx is not None:  
                    if svari==svars[0]: cv=cv[:,lonidx]
                    else: cv=cv[:,:,lonidx] 
                if sum(abs(cv)<1e3)==0: sdict[mvari].append(sdict[mvari][-1]); continue #fix nan data at this time
                #interp in space
                if mvari=='elev':
                    #remove GM nan pts
                    if ifix==0:
                        sindn,sindp=sindns[0],sindps[0]
                        cv=cv.ravel(); fpn=(abs(cv[sindn])>1e3)*(abs(cv[sindp])<1e3); cv[sindn]=cv[sindp]; fpn=abs(cv)>1e3 #init fix
                        if sum(fpn)!=0: fni=nonzero(fpn)[0]; fri=nonzero(~fpn)[0]; fpi=fri[near_pts(sxy[fni],sxy[fri])]; cv[fni]=cv[fpi] #final fix
                        cv=cv.reshape(ds)

                    v0=array([cv[idy0,idx0],cv[idy0,idx0+1],cv[idy0+1,idx0],cv[idy0+1,idx0+1]]) #find parent pts
                    for ii in arange(4): #remove nan in parent pts
                        if ifix==1: fpn=abs(v0[ii])>1e3; v0[ii,fpn]=sp.interpolate.griddata(bxy[~fpn,:],v0[ii,~fpn],bxy[fpn,:],'nearest')
                    v1=v0[0]*(1-ratx0)+v0[1]*ratx0; v2=v0[2]*(1-ratx0)+v0[3]*ratx0; vi=v1*(1-raty0)+v2*raty0 #interp
                else:
                    #remove GM nan pts
                    if ifix==0:
                        for ii in arange(nz):
                            if sum(abs(cv[ii])<1e3)==0: cv[ii]=cv[ii-1] #fix nan data for whole level
                            sindn,sindp=sindns[ii],sindps[ii]
                            if len(sindp)!=0:
                               cvi=cv[ii].ravel(); fpn=(abs(cvi[sindn])>1e3)*(abs(cvi[sindp])<1e3); cvi[sindn]=cvi[sindp]; fpn=abs(cvi)>1e3 #init fix
                               if sum(fpn)!=0: fni=nonzero(fpn)[0]; fri=nonzero(~fpn)[0]; fpi=fri[near_pts(sxy[fni],sxy[fri])]; cvi[fni]=cvi[fpi] #final fix

                    v0=array([cv[idz,idy,idx],cv[idz,idy,idx+1],cv[idz,idy+1,idx],cv[idz,idy+1,idx+1],
                              cv[idz+1,idy,idx],cv[idz+1,idy,idx+1],cv[idz+1,idy+1,idx],cv[idz+1,idy+1,idx+1]]) #find parent pts
                    for ii in arange(8): #remove nan in parent pts
                        if ifix==1: fpn=abs(v0[ii])>1e3; v0[ii,fpn]=sp.interpolate.griddata(bxyz[~fpn,:],v0[ii,~fpn],bxyz[fpn,:],'nearest',rescale=True)
                    v11=v0[0]*(1-ratx)+v0[1]*ratx;  v12=v0[2]*(1-ratx)+v0[3]*ratx; v1=v11*(1-raty)+v12*raty
                    v21=v0[4]*(1-ratx)+v0[5]*ratx;  v22=v0[6]*(1-ratx)+v0[7]*ratx; v2=v21*(1-raty)+v22*raty
                    vi=v1*(1-ratz)+v2*ratz  #interp in space
                sdict[mvari].append(vi) #save data
        C.close();
    for i in ['time',*mvar]: sdict[i]=array(sdict[i])

    #interp in time
    mtime=arange(StartT,EndT+dt,dt); nt=len(mtime)
    for mvari in mvar:
        svi=interpolate.interp1d(S.time,sdict[mvari],axis=0)(mtime)
        if iLP[n]==1: svi=lpfilt(svi,dt,fc) #low-pass
        sdict[mvari]=svi
    S.time=mtime
    for i in setdiff1d(mvar,'elev'): sdict[i]=sdict[i].reshape([nt,nobn,nvrt]) #reshape the data 

    #--------------------------------------------------------------------------
    #create netcdf
    #--------------------------------------------------------------------------
    if sname.endswith('.th.nc'):
       #define dimensions
       dimname=['nOpenBndNodes', 'nLevels', 'nComponents', 'one', 'time']
       if sname=='elev2D.th.nc':
           dims=[nobn,1,1,1,nt]; vi=S.elev[...,None,None]
       elif sname=='uv3D.th.nc':
           dims=[nobn,nvrt,2,1,nt]; vi=c_[S.u[...,None],S.v[...,None]]
       elif sname in ['TEM_3D.th.nc','SAL_3D.th.nc']:
           dims=[nobn,nvrt,1,1,nt]; vi=sdict[mvar[0]][...,None]
       nd=zdata(); nd.dimname=dimname; nd.dims=dims

       #define variables
       z=zdata(); z.attrs=['long_name']; z.long_name='time step (sec)'; z.dimname=('one',); z.val=array(dt*86400); nd.time_step=z
       z=zdata(); z.attrs=['long_name']; z.long_name='time (sec)'; z.dimname=('time',); z.val=(S.time-S.time[0])*86400; nd.time=z
       z=zdata(); z.dimname=('time','nOpenBndNodes','nLevels','nComponents'); z.val=vi.astype('float32'); nd.time_series=z
    else:
       #define dimensions
       dimname=['time','node','nLevels','one']
       dims=[nt,nobn,nvrt,1]; vi=sdict[mvar[0]][...,None]
       nd=zdata(); nd.dimname=dimname; nd.dims=dims

       #nd.vars=['time', 'map_to_global_node', 'tracer_concentration']
       z=zdata(); z.dimname=('time',); z.val=(S.time-S.time[0])*86400; nd.time=z
       z=zdata(); z.dimname=('node',); z.val=bind+1; nd.map_to_global_node=z
       z=zdata(); z.dimname=('time','node','nLevels','one'); z.val=vi.astype('float32'); nd.tracer_concentration=z

    WriteNC(sname,nd)
