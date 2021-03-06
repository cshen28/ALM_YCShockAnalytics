# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 09:34:50 2020

@author: 330411836
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 08:41:38 2020

@author: 330411836
"""
#Added 1) YTM calculator and 2) duration optimizer

#To dos:
# 1) change the table to reflect movements in returns (asset allocation)
# 2) Add key duration labels to the chart (key duration movements)
# 3) add a button to do auto duration match (optimization)
# 4) quantify the YTM rate of the asset (return rate)
# 5) Add cashflow tab

#%% Import functions and data
from CSModules import ALM_kit
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import quandl

def getfit(t1='2000-01-02', t2='2020-12-02'):
    #Load data
    df_YieldC = quandl.get(
        "USTREASURY/YIELD", authtoken="4_zrDSANo7hMt_uhyzQy")
    df_YieldC.reset_index(level=0, inplace=True)
    df_YieldC['Date'] = pd.to_datetime(df_YieldC['Date'], format="%m/%d/%Y")

    #NS Cure fit
    t_cal = df_YieldC['Date']
    i_range = np.where((t_cal > t1) & (t_cal < t2))

    t = np.array([0.08333333, 0.16666667, 0.25,
                  0.5, 1, 2, 3, 5, 7, 10, 20, 30])
    y = np.array(df_YieldC.iloc[:, 1:]).astype(float)[i_range]
    fit_par = pd.DataFrame(np.apply_along_axis(
        lambda x: ALM_kit.ns_par(t, x), axis=1, arr=y))
    return {'df_YieldC': df_YieldC, 't_cal': t_cal.iloc[i_range], 'tact': t, 'y': y, 'fit_par': fit_par}


def PVCashflow_AL(forecast_data, bond_weight=[0.363, 0.447, 0.19], N=5000):

    #Asset CF generate
    cf_bond_L, t_bond_L = ALM_kit.bond_cashflow(1000, 30, 2.5, 1)
    cf_bond_M, _ = ALM_kit.bond_cashflow(1000, 10, 2, 1)
    cf_bond_S, _ = ALM_kit.bond_cashflow(1000, 2, 1, 1)
    cf_bonds = np.array([cf_bond_L,
                         np.append(cf_bond_M, np.repeat(
                             0, cf_bond_L.shape[0]-cf_bond_M.shape[0])),
                         np.append(cf_bond_S, np.repeat(0, cf_bond_L.shape[0]-cf_bond_S.shape[0]))])
    cf_weights = np.array(bond_weight)  # Bond weight (Duration matched)
    cf_singleasset = np.dot(cf_weights, cf_bonds)

    #Liabilty CF generate
    df_mort = pd.read_csv("Mx_2019.csv", sep=',')
    cf_liability, t_liability = ALM_kit.liability_cashflow(
        df_mort.loc[60:]['Total'], 3000*12)

    LCF_base,LDur_base = ALM_kit.PV_cashflow(cf_liability, t_liability,
                               fit_ns=forecast_data['fit_par'])
    ACF_base,ADur_base = ALM_kit.PV_cashflow(cf_singleasset, t_bond_L,
                               fit_ns=forecast_data['fit_par'])
    if N>1:                           
        n_A = LCF_base/ACF_base
        #PV
        LCF = [ALM_kit.PV_cashflow(cf_liability, t_liability,
                                fit_ns=forecast_data['Var_fit_par'][i]) for i in range(N)]
        ACF = [ALM_kit.PV_cashflow(cf_singleasset*n_A, t_bond_L,
                                fit_ns=forecast_data['Var_fit_par'][i]) for i in range(N)]
    else:
        n_A = None
        LCF = [(None,None),(None,None)]
        ACF = [(None,None),(None,None)]
    
    return {'cf_asset': cf_singleasset, 'cf_liability': cf_liability, 't_asset': t_bond_L, 't_liability': t_liability, 'ACFP': np.array(ACF)[:,0], 'LCFP': np.array(LCF)[:,0],'LDur':LDur_base,'ADur':ADur_base}


#%%






#%% Figures

tPar = np.linspace(0, 30, 50)
key_dur = np.array([2, 10, 30])
key_weights = 25*cf_weights/np.sum(cf_weights)

yield_t1 = ALM_kit.yfit_beta(tPar, fit_par[t1])
yield_t2 = ALM_kit.yfit_beta(tPar, fit_par[t1])
y_line = [np.min([yield_t1.min(), yield_t2.min()]),
          np.max([yield_t1.max(), yield_t2.max()])]


fig = make_subplots(
    rows=3, cols=2,
    subplot_titles=("Yield Curve & Cash Flow", "Performance Attribution"),
    specs=[
        [{"type": "xy", "secondary_y": True, "rowspan": 3},{"type": "table"}],
        [None, {"type": "table", "rowspan": 2}],
        [None, None]
    ]
)

#Yield Curves
fig.add_trace(go.Scatter(x=tPar, y=ALM_kit.yfit_beta(
    tPar, fit_par[t1]), mode='lines', line=dict(color='red'), showlegend=False), row=1, col=1)
fig.add_trace(go.Scatter(x=tPar, y=ALM_kit.yfit_beta(
    tPar, fit_par[t2]), mode='lines', line=dict(color='blue'), showlegend=False), row=1, col=1)

fig.add_trace(go.Scatter(x=t, y=y[t1], mode='markers', marker=dict(
    color='red'), name='Raw yield 1'), row=1, col=1)
fig.add_trace(go.Scatter(x=t, y=y[t2], mode='markers', marker=dict(
    color='blue'), name='Raw yield 2'), row=1, col=1)


#Cash flow
x_a = t_bond_L
y_a = N_bond*cf_singleasset
y_l = cf_liability
x_l = t_liability

fig.add_trace(go.Scatter(x=x_a, y=y_a, visible=False,line=dict(color='green'),
                         name='Cashflow - Asset'), secondary_y=False)
fig.add_trace(go.Scatter(x=x_l, y=y_l, visible=False,line=dict(color='black'),
                         name='Cashflow - Liability'), secondary_y=True)

fig.add_trace(go.Table(
    header=dict(values=list(['PV', 'Asset', 'Liability', 'AL-Mismatch']),
                fill_color='paleturquoise',
                align='left'),
    cells=dict(values=[['Yield 1', 'Yield 2'],
                       PV_asset_t1t2_text,
                       PV_liabilities_t1t2_text,
                       PV_ALMis_text],
               fill_color='lavender',
               align='left')),
              row=1, col=2)

fig.add_trace(go.Table(
    header=dict(values=list(['%Movement <br>(y1 to y2)', 'Asset', 'Liability']),
                fill_color='paleturquoise',
                align='left'),
    cells=dict(values=[['Level', 'Slope', 'Curvature', 'Tau', '<b>Total</b>'],
                       movement_asset,
                       movement_liability],
               fill_color='lavender',
               align='left')),
              row=2, col=2)

#Button switch
fig.update_layout(
    autosize=False,
    width=1200,
    height=500,
    updatemenus=[
        dict(
            buttons=list([
                dict(label="Yield Curve",
                     method="update",
                     args=[{'visible': [True, True, True, True, False, False]}
                           ]
                     ),
                dict(label="Cash flow",
                     method="update",
                     args=[
                         {'visible': [False, False, False, False, True, True]}
                     ]
                     )
            ]
            ), yanchor="top", xanchor="left", y=1.25, x=0
        )
    ])

fig.update_layout(legend_orientation="h")




# %%
