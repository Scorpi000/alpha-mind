# -*- coding: utf-8 -*-
"""
Created on 2017-8-23

@author: cheng.li
"""

import numpy as np
import pandas as pd
from PyFin.api import *
from alphamind.api import *
from matplotlib import pyplot as plt


# defind your alpha formula here
base_factors = ['EPS', 'ROEDiluted', 'BTOP']#, 'ROEDiluted', 'VAL', 'CFinc1']

expression = 0.

for name in base_factors:
    expression = expression + LAST(name)

alpha_factor_name = 'alpha_factor'
alpha_factor = {alpha_factor_name: expression}

# end of formula definition

engine = SqlEngine('postgresql+psycopg2://postgres:A12345678!@10.63.6.220/alpha')
universe = Universe('custom', ['zz500'])
benchmark_code = 905
neutralize_risk = ['SIZE'] + industry_styles
freq = '1w'
n_bins = 5

if freq == '1m':
    horizon = 21
elif freq == '1w':
    horizon = 4
elif freq == '1d':
    horizon = 0

dates = makeSchedule('2012-01-01',
                     '2012-08-01',
                     tenor=freq,
                     calendar='china.sse')

factor_all_data = engine.fetch_data_range(universe,
                                          alpha_factor,
                                          dates=dates,
                                          benchmark=905)['factor']
return_all_data = engine.fetch_dx_return_range(universe, dates=dates, horizon=horizon)

factor_groups = factor_all_data.groupby('trade_date')
return_groups = return_all_data.groupby('trade_date')
final_res = np.zeros((len(dates), n_bins))

for i, value in enumerate(factor_groups):
    date = value[0]
    data = value[1][['code', alpha_factor_name, 'isOpen', 'weight'] + neutralize_risk]
    codes = data.code.tolist()
    ref_date = value[0].strftime('%Y-%m-%d')
    returns = return_groups.get_group(date)

    total_data = pd.merge(data, returns, on=['code']).dropna()
    risk_exp = total_data[neutralize_risk].values.astype(float)
    dx_return = total_data.dx.values
    benchmark = total_data.weight.values

    f_data = total_data[[alpha_factor_name]]
    try:
        er = factor_processing(total_data[[alpha_factor_name]].values,
                               pre_process=[winsorize_normal, standardize],
                               risk_factors=risk_exp,
                               post_process=[standardize])
        res = er_quantile_analysis(er,
                                   n_bins=n_bins,
                                   dx_return=dx_return,
                                   benchmark=benchmark)
    except Exception as e:
        print(e)
        res = np.zeros(n_bins)

    final_res[i] = res / benchmark.sum()

df = pd.DataFrame(final_res, index=dates)

start_date = advanceDateByCalendar('china.sse', dates[0], '-1w')
df.loc[start_date] = 0.
df.sort_index(inplace=True)
df = df.cumsum().plot()
plt.show()