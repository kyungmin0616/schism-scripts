from pylib import *

S=loadz('RUN12a_vert.npz'); S.time=S.time+datenum(2016,9,8)
tran=2
sname='Vert/images/FL'


depth=array(S.zcor[tran]); lon=S.xy[tran][0,:]
lon=(ones(shape(depth[0])).transpose()*lon).transpose()

for i,ctime in enumerate(S.time):
    figure(1)
    clf()
    contourf(lon,depth[i],array(S.temp[tran][i]),cmap='jet',levels=linspace(0,30,50),extend='both');
    colorbar();
    xlim([-76.5,-74.8])
    #xlim([-80.5,-77]); 
    ylim([-1000,0]);
    title(num2date(ctime))
    savefig('{}/{}'.format(sname,num2date(ctime).strftime('%Y%m%d%H%M%S')) + '.png',bbox_inches='tight')
    close()




