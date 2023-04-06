from pylib import *
import pandas as pd

dir_obs='/rcfs/projects/mhk_modeling/dataset/NOAA/FloridaCurrent/FC_cable_transport_2016.dat'
StartT=datenum('2016-9-8')
#StartT=datenum('1950-01-01')
st=datenum(2016,9,24)
se=datenum(2016,10,21)
#runs=['RUN01a_flux.out','RUN01b_flux.out','RUN01c_flux.out','RUN01d_flux.out','RUN01e_flux.out']
#runs=['RUN01e_flux.out','RUN02a_flux.out','RUN03a_flux.out','RUN04a_flux.out']
#runs=['RUN01e_flux.out','RUN04c_flux.out','RUN01b_flux.out','RUN01a_flux.out','Paper_flux.npz']
runs=['RUN06f_flux.out','CMEMS_flux.npz','HYCOM_FLUX.npz']
ym=[0,40.0]
colors='kgbcm'

#font size
SMALL_SIZE = 15
MEDIUM_SIZE = 15
BIGGER_SIZE = 15

#rc('font', family='Helvetica')
rc('font', size=SMALL_SIZE)  # controls default text sizes
rc('axes', titlesize=SMALL_SIZE)  # fontsize of the axes title
rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

#read obs results
obs=npz_data(); Data=loadtxt(dir_obs,skiprows=35); obs.fc=Data[:,3]
obs.time=[]
for n in arange(len(Data)):
    obs.time.append(datenum(str(Data[n,0].astype('int'))+'-'+str(Data[n,1].astype('int'))+'-'+str(Data[n,2].astype('int'))))

#read model results
Model=[]
for m, run in enumerate(runs):
    if run.endswith('.npz'):
       if m==len(runs)-1: Si=loadz('{}'.format(run)); Si.time=Si.time/24+datenum(2000,1,1); Si.flux=-squeeze(Si.flux)/1000000
       elif m==len(runs)-2: Si=loadz('{}'.format(run)); Si.time=Si.time/24+datenum(1950,1,1); Si.flux=-squeeze(Si.flux)/1000000
       else: Si=loadz('{}'.format(run)); Si.time=Si.time+StartT; Si.flux=-squeeze(Si.flux)/1000000
    elif run.endswith('.out'):
#       if m==3: StartT=datenum(2016,8,1)
#       else: StartT=datenum(2016,9,8)
       Si=npz_data(); Data=loadtxt(run); Si.time=Data[:,0]+StartT; Si.flux=Data[:,1:]/1000000
    else: print('Wrong data type')
    Model.append(Si)

#daily mean
#for m, run in enumerate(runs):
#    times=array([num2date(i).strftime('%Y-%m-%d %H:%M:%S') for i in Model[m].time])
#    times=pd.to_datetime(times); data=Model[m].flux
#    df = pd.DataFrame(data=data,index=times); means=df.groupby(df.index.floor('D')).mean()
#    times=array(datenum(means.index.astype(str))); mfc=means.values
#    Model[m].time=times; Model[m].flux=mfc


#plot
figure(1,figsize=[18,9])
clf()
plot(obs.time,obs.fc,'r',lw=3)
for n, run in enumerate(runs):
    #myi = smooth(myi, 360)
    if n==len(runs)-1: Model[n].flux=lpfilt(Model[n].flux,1/24,13/24)
    plot(Model[n].time,Model[n].flux,color=colors[n],lw=3)
gca().xaxis.grid('on')
gca().yaxis.grid('on')
xts, xls = get_xtick(fmt=2, xts=arange(st, se+15,15), str='%m/%d')
setp(gca(), xticks=xts, xticklabels=xls, xlim=[st, se],ylim=ym)
legend(['NOAA cable',*runs])
#legend(['NOAA cable','SCHISM'])
xlabel('Date (2020)')
ylabel('Sv')
show()