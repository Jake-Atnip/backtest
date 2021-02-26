'''Author: Jacob Atnip'''
import pandas as pd
from copy import deepcopy
from tqdm import tqdm
import numpy as np
import pandas_market_calendars as mcal


backtest_instructions = '''Using the backtester
1. create a Backtest() object. Pass your strategy name. i.e. Backtest(strategy = your_strategy_class_name)
2. load your data with backtest.datahandler.load_data_from_excel(data_file_path,bars_to_load)
3. create your strategy class via inheritance from the Strategy class. i.e. your_strategy_class_name(Strategy):
4. code your strategy rules within a method called def strategy_logic(self)
3. run your strategy with backtest.test_strategy(), pass the starting cash you'd like or it will default to $100,000

Using the optimizer
1. create and Optimize() object
2. create your strategy class via inheritance from the Strategy class. i.e. your_strategy_class_name(Strategy):
3. your strategy_logic function should include the following parameters def strategy_logic(self, par1, par2): where par1 and par2 are values for two parameters in your strategy
4. write the rules for your strategy. Be sure to use the par1 and par2 parameter references
5. run Optimize.create_optimization_table method('para name 1',par1 range,'para name 2',par2 range, your_strategy_class_name,data_file_path, starting cash)'''


class Optimize:

    def create_optimization_table(self,par1,par1_range,par2,par2_range,strat_name,data_file_path,cash):

        bars_to_load = max(max(par1_range),max(par2_range))+1

        self.optimization_table_max_drawdown = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_max_drawdown.index.name = str(par1)
        self.optimization_table_max_drawdown.columns.name = str(par2)

        self.optimization_table_CAGR = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_CAGR.index.name = str(par1)
        self.optimization_table_CAGR.columns.name = str(par2)

        self.optimization_table_CAGRMDD = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_CAGRMDD.index.name = str(par1)
        self.optimization_table_CAGRMDD.columns.name = str(par2)

        no_of_iterations = len(par1_range)*len(par2_range)
        q = 1

        for i, val1 in enumerate(par1_range):
            for j, val2 in enumerate(par2_range):
                print('starting iteration '+str(q)+' of '+str(no_of_iterations))
                opt = Backtest(strategy = strat_name)
                opt.datahandler.load_data_from_excel(data_file_path,bars_to_load)
                opt._optimize_strategy(val1,val2,cash)

                opt.analysis._calc_CAGRMDD()

                max_drawdown = opt.analysis.max_drawdown
                CAGR = opt.analysis.CAGR
                CAGRMDD = opt.analysis.CAGRMDD

                self.optimization_table_max_drawdown.iloc[i,j] = max_drawdown
                self.optimization_table_CAGR.iloc[i,j] = CAGR
                self.optimization_table_CAGRMDD.iloc[i,j] = CAGRMDD

                q+=1

class Analysis:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.account = backtest.account
        self.backtest = backtest

    def analyze(self):
        pass

    def _create_underwater_plot(self):
        underwater_plot = self.account.account_results.loc[:,['value']]
        underwater_plot.loc[:,'max'] = 0
        for i in range(len(self.portfolio.results)):
            max_val = self.portfolio.results.iloc[0:i,0].max()
            underwater_plot.iloc[i-1,1] = max_val
        underwater_plot.iloc[-1,1] = underwater_plot.iloc[:,0].max()
        self.underwater_plot = underwater_plot

    def _calc_drawdown(self):
        self._create_underwater_plot()
        self.drawdown_df = -(1-(self.underwater_plot.loc[:,'portfolio value']/self.underwater_plot.loc[:,'max']))
        self.max_drawdown = self.drawdown_df.min()

    def _calc_CAGR(self):
        end_val = self.account.account_results.loc[self.datahandler.strategy_end_date,'value']
        start_val = self.account.account_results.loc[self.datahandler.strategy_start_date,'value']
        no_of_years = (self.account.account_results.index[-1] - self.account.account_results.index[0]).days/365
        self.CAGR = ((end_val/start_val)**(1/no_of_years))-1

    def _calc_CAGRMDD(self):
        self._calc_drawdown()
        self._calc_CAGR()
        self.CAGRMDD = -(self.CAGR/self.max_drawdown)


    def results_overview(self):
        pass

class Strategy:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def strategy_logic_begin(self):
        print('Make sure to add the parameter strategy = yourstrategyname when creating an instance of the Backtest class')
    
    def strategy_logic_end(self):
        print('Make sure to add the parameter strategy = yourstrategyname when creating an instance of the Backtest class')
        
class Account:
    
    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.analysis = backtest.analysis
        self.strategy = backtest.strategy
        self.backtest = backtest
        
    def _reset_account(self, cash = 100000):
        self.assets = {'cash':cash}
        self.liabilities = {'borrowed funds':0}
        self.equity = {'account value':cash}
        self.account_history = pd.DataFrame({'assets':[() for i in self.datahandler.date_index],'liabilities':[() for i in self.datahandler.date_index],'equity':[() for i in self.datahandler.date_index]},index = self.datahandler.date_index)
        self.account_history.iloc[0,0] = (deepcopy(self.assets),)
        self.account_history.iloc[0,1] = (deepcopy(self.liabilities),)
        self.account_history.iloc[0,2] = (deepcopy(self.equity),)
        self.account_results = pd.DataFrame({'cash':[() for i in self.datahandler.date_index],'value':[() for i in self.datahandler.date_index]},index = self.datahandler.date_index)

    def _remove_delisted_securities(self):
        del_list1 = []
        #consider adding order series adjustments here
        for asset in self.assets:
            if asset != 'cash' and asset not in self.datahandler.available_symbols:
                del_list1.append(asset)
                if self.assets[asset]['value'] >= self.liabilities['borrowed funds']:
                            self.assets['cash'] = self.assets['cash']+self.assets[asset]['value'] - self.liabilities['borrowed funds']
                            self.liabilities['borrowed funds'] = 0
                else:
                    self.liabilities['borrowed funds'] = self.liabilities['borrowed funds'] - self.assets[asset]['value']

        for asset in del_list1:
            del self.assets[asset]

        #now do liabilities (aka shorts) 
        del_list2 = []
        for liability in self.liabilities:
            if liability != 'borrowed funds' and liability not in self.datahandler.available_symbols:
                del_list2.append(liability)
                if self.liabilities[liability]['value'] <= self.assets['cash']:
                            self.assets['cash'] = self.assets['cash'] - self.liabilities[liability]['value'] 

                else:
                    self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+(self.liabilities[liability]['value']  - self.assets['cash'])
                    self.assets['cash'] = 0

        for liability in del_list2:
            del self.liabilities[liability]
            
        pending_orders = [order for order in self.execution.pending_orders if self.execution.pending_orders[order]['symbol'] in del_list1 or self.execution.pending_orders[order]['symbol']  in del_list2]
        for order in pending_orders:
            del self.execution.pending_orders[order]
            

    def _update_account_begin(self):

        values = []

        for asset in self.assets:
            if asset != 'cash':
                asset_data = self.assets[asset]
                asset_data['value'] = self.assets[asset]['quantity']*self.datahandler.open_data[asset][self.datahandler.current_date]
                values.append(asset_data['value'])
                self.assets[asset].update(asset_data)

        for liability in self.liabilities:
            if liability != 'borrowed funds':
                liability_data = self.liabilities[liability]
                liability_data['value'] = self.liabilities[liability]['quantity']*self.datahandler.open_data[liability][self.datahandler.current_date]
                values.append(-liability_data['value'])
                self.liabilities[liability].update(liability_data)

        self.equity['account value'] = sum(values)+self.assets['cash']-self.liabilities['borrowed funds']
        
        
        self.portfolio.positions = []
        for asset in self.assets:
            if asset !='cash':
                self.portfolio.positions.append(asset)
        for liabilitiy in self.liabilities:
            if liability != 'borrowed funds':
                self.portfolio.positions.append(liability)
        self.portfolio.positions = tuple(self.portfolio.positions)

    def _update_account_end(self):

        values = []

        for asset in self.assets:
            if asset != 'cash':
                asset_data = self.assets[asset]
                asset_data['value'] = self.assets[asset]['quantity']*self.datahandler.close_data[asset][self.datahandler.current_date]
                values.append(asset_data['value'])
                self.assets[asset].update(asset_data)

        for liability in self.liabilities:
            if liability != 'borrowed funds':
                liability_data = self.liabilities[liability]
                liability_data['value'] = self.liabilities[liability]['quantity']*self.datahandler.close_data[liability][self.datahandler.current_date]
                values.append(-liability_data['value'])
                self.liabilities[liability].update(liability_data)

        self.equity['account value'] = sum(values)+self.assets['cash']-self.liabilities['borrowed funds']
        
        self.portfolio.positions = []
        for asset in self.assets:
            if asset !='cash':
                self.portfolio.positions.append(asset)
        for liabilitiy in self.liabilities:
            if liability != 'borrowed funds':
                self.portfolio.positions.append(liability)
        self.portfolio.positions = tuple(self.portfolio.positions)
        
    def _update_account_history_and_results(self):
        self.account_history.loc[self.datahandler.current_date,'assets'] = (deepcopy(self.assets),)
        self.account_history.loc[self.datahandler.current_date,'liabilities'] = (deepcopy(self.liabilities),)
        self.account_history.loc[self.datahandler.current_date,'equity'] = (deepcopy(self.equity),)
        self.account_results.loc[self.datahandler.current_date,'cash'] = self.assets['cash']
        self.account_results.loc[self.datahandler.current_date,'value'] = self.equity['account value']
    


    def _calculate_change_cost_basis_and_new_ladder_FIFO(self,shares,ladder):
        share_count = 0
        cost = 0
        change = 0
        for i,pairs in enumerate(ladder):
            shs = pairs[0]
            cst = shs*pairs[1]
            share_count = share_count + shs
            cost = cst+cost
            if shares <= share_count:
                diff = share_count - shares
                change = cost - diff*pairs[1]
                break
                
        if diff != 0:
            ladder[i] = (diff,ladder[i][1])
            j = i-1
        else:
            j = i
            
        if j == 0:
            del ladder[j]
        else:
            ij = len(ladder) - j
            for s in range(j+1):
                del ladder[-ij]

        return (change,ladder)
    
    def _update_account_with_order(self,order):

        if order['symbol'] not in self.assets and order['symbol'] not in self.liabilities:
            start_of_position  = True

            if order['quantity'] >0:
                desired_side = 'long'
                quantity = order['quantity']
                value = abs(quantity*order['execution price'])
                cost_basis = value
                ladder = [(abs(quantity),order['execution price'])]
                pos_dict = {'value':value,
                'quantity':quantity,
                'start of position':self.datahandler.current_date,
                'most recent order':order,
                'cost basis':cost_basis,
                'ladder':ladder}
                if value <= self.assets['cash']:
                    self.assets['cash'] = self.assets['cash'] - value
                    self.assets[order['symbol']] = pos_dict
                else:
                    self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+(value - self.assets['cash'])
                    self.assets['cash'] = 0
                    self.assets[order['symbol']] = pos_dict


            elif order['quantity'] < 0:
                desired_side = 'short'
                quantity = order['quantity']
                value = abs(quantity*order['execution price'])
                cost_basis = value
                ladder = [(abs(quantity),order['execution price'])]
                pos_dict = {'value':value,
                'quantity':quantity,
                'start of position':self.datahandler.current_date,
                'most recent order':order,
                'cost basis':cost_basis,
                'ladder':ladder}
                self.assets['cash'] = self.assets['cash']+value
                self.liabilities[order['symbol']] = pos_dict

        else:
            start_of_position = False
            if order['symbol'] in self.assets:
                current_side = 'long'

                if order['quantity'] + self.assets[order['symbol']]['quantity'] > 0:
                    desired_side = 'long'
                    quantity = abs(order['quantity'] + self.assets[order['symbol']]['quantity'])
                    value = quantity*order['execution price']
                    if order['quantity'] > 0:
                        cost_basis = abs(order['quantity'])*order['execution price'] + self.assets[order['symbol']]['cost basis']
                        ladder = self.assets[order['symbol']]['ladder'] + [(abs(order['quantity']),order['execution price'])]
                        if (order['quantity']*order['execution price']) <= self.assets['cash']:
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                        else:
                            self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                            self.assets['cash'] = 0

                    else:
                        cost_basis_change,ladder = self._calculate_change_cost_basis_and_new_ladder_FIFO(abs(order['quantity']),self.assets[order['symbol']]['ladder'])
                        cost_basis = self.assets[order['symbol']]['cost basis'] - cost_basis_change
                        if (abs(order['quantity'])*order['execution price']) >= self.liabilities['borrowed funds']:
                            self.assets['cash'] = self.assets['cash']+((abs(order['quantity'])*order['execution price']) - self.liabilities['borrowed funds'])
                            self.liabilities['borrowed funds'] = 0
                        else:
                            self.liabilities['borrowed funds'] = self.liabilities['borrowed funds'] - ((abs(order['quantity'])*order['execution price']))

                    pos_dict = {'value':value,
                    'quantity':quantity,
                    'most recent order':order,
                    'cost basis':cost_basis,
                    'ladder':ladder}

                    self.assets[order['symbol']].update(pos_dict)

                elif order['quantity'] + self.assets[order['symbol']]['quantity'] <0:
                    desired_side = 'short'
                    quantity = abs(order['quantity'] + self.assets[order['symbol']]['quantity'])
                    value = quantity*order['execution price']
                    cost_basis = value
                    ladder = [(quantity,order['execution price'])]
                    pos_dict = {'value':value,
                    'quantity':quantity,
                    'start of position':self.datahandler.current_date,
                    'most recent order':order,
                    'cost basis':cost_basis,
                    'ladder':ladder}
                    if (self.assets[order['symbol']]['quantity']*order['execution price']) >= self.liabilities['borrowed funds']:
                            self.assets['cash'] = self.assets['cash'] + ((self.assets[order['symbol']]['quantity']*order['execution price']) - self.liabilities['borrowed funds']) + (quantity*order['execution price'])
                            self.liabilities['borrowed funds'] = 0
                    else:
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds'] - (self.assets[order['symbol']]['quantity']*order['execution price'])
                        self.assets['cash'] = self.assets['cash'] + quantity*order['execution price']


                    del self.assets[order['symbol']]
                    self.liabilities[order['symbol']] = pos_dict


                elif (order['quantity'] + self.assets[order['symbol']]['quantity'])==0:
                    self.assets['cash'] = self.assets['cash'] + abs(order['quantity'])*order['execution price']
                    del self.assets[order['symbol']]

            elif order['symbol'] in self.liabilities:
                current_side = 'short'

                if order['quantity'] + (-self.liabilities[order['symbol']]['quantity']) > 0:
                    desired_side = 'long'
                    quantity = abs(order['quantity'] + (-self.liabilities[order['symbol']]['quantity']))
                    value = quantity*order['execution price']
                    cost_basis = value
                    ladder = [(quantity,order['execution price'])]
                    pos_dict = {'value':value,
                    'quantity':quantity,
                    'start of position':self.datahandler.current_date,
                    'most recent order':order,
                    'cost basis':cost_basis,
                    'ladder':ladder}
                    if (order['quantity']*order['execution price']) <= self.assets['cash']:
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                    else:
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                        self.assets['cash'] = 0

                    del self.liabilities[order['symbol']]
                    self.assets[order['symbol']] = pos_dict


                elif order['quantity'] + (-self.liabilities[order['symbol']]['quantity']) <0:
                    desired_side = 'short'
                    quantity = abs(order['quantity'] + (-self.liabilities[order['symbol']]['quantity']))
                    value = quantity*order['execution price']
                    if order['quantity'] > 0:
                        cost_basis_change,ladder = self._calculate_change_cost_basis_and_new_ladder_FIFO(abs(order['quantity']),self.liabilities[order['symbol']]['ladder'])
                        cost_basis = self.liabilities[order['symbol']]['cost basis'] - cost_basis_change
                        if (order['quantity']*order['execution price']) <= self.assets['cash']:
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                        else:
                            self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                            self.assets['cash'] = 0
                        
                    else:
                        cost_basis = abs(order['quantity'])*order['execution price'] + self.liabilities[order['symbol']]['cost basis']
                        ladder = self.liabilities[order['symbol']]['ladder'] + [(abs(order['quantity']),order['execution price'])]
                        self.assets['cash'] = self.assets['cash']+abs(order['quantity'])*order['execution price']

                    pos_dict = {'value':value,
                    'quantity':quantity,
                    'most recent order':order,
                    'cost basis':cost_basis,
                    'ladder':ladder}

                    self.liabilities[order['symbol']].update(pos_dict)

                elif order['quantity'] + (-self.liabilities[order['symbol']]['quantity'])==0:
                    if (order['quantity']*order['execution price']) <= self.assets['cash']:
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                    else:
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                        self.assets['cash'] = 0
                    del self.liabilities[order['symbol']]


class Portfolio:

    def _create_pointers(self,backtest):
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def _reset_portfolio(self,cash):
        self.positions = ()
            
class Execution:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest
    
    def _clear_pending_orders(self):
        self.pending_orders = {}
        self._most_recent_ID = 0
        
    def _add_pending_order(self,order):
        order_ID = order['Order ID']
        self.pending_orders[order_ID] = deepcopy(order)
            
    def _execute_order(self,order):
        self.account._update_account_with_order(order)
                
    def _scan_and_execute_pending_orders(self):
        removal_list = []
        for ID in self.pending_orders:
            order = self.pending_orders[ID]
            order_type = order['order type']
            
            if order_type == 'market':
                market_order_type = order['desired execution time']
                if market_order_type == 'open':
                    if self.datahandler._tob == 'begin':
                        sym = order['symbol']
                        sym_open_data = self.datahandler.open_data[sym]
                        execution_price = sym_open_data.loc[self.datahandler.current_date]
                        order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'begin'})
                        self._update_order_series(order)
                        self._execute_order(order)
                        removal_list.append(ID)
                elif market_order_type == 'close':
                    if self.datahandler._tob == 'end':
                        sym = order['symbol']
                        sym_close_data = self.datahandler.close_data[sym]
                        execution_price = sym_close_data.loc[self.datahandler.current_date]
                        order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'end'})
                        self._update_order_series(order)
                        self._execute_order(order)
                        removal_list.append(ID)

        self._update_pending_orders(removal_list)
        
    def _update_pending_orders(self,removal_list):
        for ID in removal_list:
            del self.pending_orders[ID]

    def _gen_order_ID(self):
        ID = self._most_recent_ID
        self._most_recent_ID = self._most_recent_ID + 1
        return ID

    def _update_order_series(self,order):

        if self.order_series.loc[self.datahandler.current_date] != ('No orders',):
            self.order_series.loc[self.datahandler.current_date] = (self.order_series.loc[self.datahandler.current_date] +(order,))

        elif self.order_series.loc[self.datahandler.current_date] == ('No orders',):
            self.order_series.loc[self.datahandler.current_date] = (order,)

    def _update_pending_order_series(self,order):

        if self.pending_order_series.loc[self.datahandler.current_date] != ('No pending orders',):
            self.pending_order_series.loc[self.datahandler.current_date] = (self.pending_order_series.loc[self.datahandler.current_date] +(order,))

        elif self.pending_order_series.loc[self.datahandler.current_date] == ('No pending orders',):
            self.pending_order_series.loc[self.datahandler.current_date] = (order,)

    def market_order(self,symbol,quantity,time):

        ID = self._gen_order_ID()

        order = {'Order ID': ID,
        'date of placement':self.datahandler.current_date,
        'time of placement':self.datahandler._tob,
        'order type':'market',
        'symbol':symbol,
        'quantity':quantity,
        'desired execution time':time}

        self._update_pending_order_series(order)
        
        if order['desired execution time'] == 'open':
            if order['time of placement'] == 'begin':
                sym = order['symbol']
                sym_open_data = self.datahandler.open_data[sym]
                execution_price = sym_open_data.loc[self.datahandler.current_date]
                order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'begin'})
                self._update_order_series(order)
                self._execute_order(order)
                
            elif order['time of placement'] == 'end':
                self._update_pending_order_series(order)
                most_recent_order = (self.pending_order_series.loc[self.datahandler.current_date])[-1]
                self._add_pending_order(most_recent_order)
                
                
        elif order['desired execution time'] == 'close':
            if order['time of placement'] == 'end':
                sym = order['symbol']
                sym_close_data = self.datahandler.close_data[sym]
                execution_price = sym_close_data.loc[self.datahandler.current_date]
                order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'end'})
                self._update_order_series(order)
                self._execute_order(order)
                
            elif order['time of placement'] == 'begin':
                self._update_pending_order_series(order)
                most_recent_order = (self.pending_order_series.loc[self.datahandler.current_date])[-1]
                self._add_pending_order(most_recent_order)

class DataHandler:

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def _create_date_iter(self):
        self._date_iter = iter(self.date_index)
        self._tob = ''
        
    def _update_begin_bar_data(self):
        if self.current_date >= self.strategy_start_date:
            self.open_data = self.open_series[list(self.available_symbols)]
            self.open_data = (self.open_data).map(lambda se: se.loc[se.index <= self.current_date])
            self.open_data = (self.open_data).map(lambda se: se.iloc[-(self._bars_to_load):])
        self._tob = 'begin'
            
    def _update_end_bar_data(self):
        if self.current_date >= self.strategy_start_date:
            self.high_data = self.high_series[list(self.available_symbols)]
            self.low_data = self.low_series[list(self.available_symbols)]
            self.close_data = self.close_series[list(self.available_symbols)]
            self.volume_data = self.volume_series[list(self.available_symbols)]
            self.high_data = (self.high_data).map(lambda se: se.loc[se.index <= self.current_date])
            self.high_data = (self.high_data).map(lambda se: se.iloc[-(self._bars_to_load):])
            self.low_data = (self.low_data).map(lambda se: se.loc[se.index <= self.current_date])
            self.low_data = (self.low_data).map(lambda se: se.iloc[-(self._bars_to_load):])
            self.close_data = (self.close_data).map(lambda se: se.loc[se.index <= self.current_date])
            self.close_data = (self.close_data).map(lambda se: se.iloc[-(self._bars_to_load):])
            self.volume_data = (self.volume_data).map(lambda se: se.loc[se.index <= self.current_date])
            self.volume_data = (self.volume_data).map(lambda se: se.iloc[-(self._bars_to_load):])

        self._tob = 'end'

    def _update_date_symbols(self):
        self.current_date = next(self._date_iter)
        if self.current_date >= self.strategy_start_date:
            self.available_symbols = []
            for sym in self.sym_list:
                if self.current_date in self.open_series[sym].index:
                    sym_dates = pd.Series(self.open_series[sym].index)
                    idx = sym_dates[sym_dates == self.current_date].index[0]
                    if (idx+1) >=self._bars_to_load:
                        self.available_symbols.append(sym)
            self.available_symbols = tuple(self.available_symbols)

    def _adjust_dates_and_transform_data(self,data_df,bars_to_load,freq):
        if 'min' in freq or 'T' in freq:
            raise AttributeError('This frequency currently not supported')
        elif 'H' in freq:
            raise AttributeError('This frequency currently not supported')
        elif freq == '1D':
            
            '''start_dates = []
            end_dates = []
            print('cleaning dates')
            for ticker in tqdm(data_df.symbol.unique()):
                
                sym = data_df.loc[data_df.symbol == ticker,:]
                sym_dates = list(sym.index)
                begin_date = sym_dates[0]
                end_date = sym_dates[-1]
                start_dates.append(begin_date)
                end_dates.append(end_date)
            start_date = min(start_dates)
            end_date = max(end_dates)'''
            cleaned_dates = data_df.index.unique()
            start_date = min(cleaned_dates)
            end_date = max(cleaned_dates)
            '''
            nyse = mcal.get_calendar('NYSE')
            sch = nyse.schedule(start_date = start_date, end_date = end_date)
            indx = mcal.date_range(sch, frequency='1D')

            cleaned_dates = []
            for date in indx:
                clean_date = pd.Timestamp(str(date.month)+'/'+str(date.day)+'/'+str(date.year))
                cleaned_dates.append(clean_date)
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)
            for date in data_df.index.unique():
                if date not in cleaned_dates:
                    raise ValueError('You have provided market data that has non-trading days')
            '''

        elif freq =='1W':
            
            start_dates = []
            end_dates = []
            for ticker in data_df.symbol.unique():
                
                sym = data_df.loc[data_df.symbol == ticker,:]
                sym_dates = list(sym.index)
                begin_date = sym_dates[0]
                end_date = sym_dates[-1]
                start_dates.append(begin_date)
                end_dates.append(end_date)

            start_date = min(start_dates)
            end_date = max(end_dates)

            days_to_add = 4-end_date.dayofweek
            adj_end_date = end_date + pd.Timedelta(str(days_to_add)+' days')

            nyse = mcal.get_calendar('NYSE')
            sch = nyse.schedule(start_date = start_date, end_date = adj_end_date)
            indx = mcal.date_range(sch, frequency='1D')

            cleaned_dates = []
            for date in indx:
                clean_date = pd.Timestamp(str(date.month)+'/'+str(date.day)+'/'+str(date.year))
                cleaned_dates.append(clean_date)
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)
            ilist = []
            for i in range(len(cleaned_dates.dayofweek)):
                if i >0:
                    prev_val = cleaned_dates.dayofweek[i-1]
                    cur_val = cleaned_dates.dayofweek[i]
                    if cur_val<prev_val:
                        ilist.append(i-1)
            ilist.append(i)
            cleaned_dates = cleaned_dates[ilist]
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)

            paired_dates = pd.Series(cleaned_dates,index = data_df.index.unique())

            new_index = pd.DatetimeIndex([paired_dates[date] for date in data_df.index])
            data_df.index = new_index

        elif freq == '1M':

            start_dates = []
            end_dates = []
            for ticker in data_df.symbol.unique():
                
                sym = data_df.loc[data_df.symbol == ticker,:]
                sym_dates = list(sym.index)
                begin_date = sym_dates[0]
                end_date = sym_dates[-1]
                start_dates.append(begin_date)
                end_dates.append(end_date)

            start_date = adj_start_date =  min(start_dates)
            end_date =  adj_end_date =  max(end_dates)
            
            if end_date.day <28:
                adj_end_date = end_date + pd.Timedelta(str(32)+' days')

            else:
                start_day = adj_start_date.dayofweek
                if start_day == 5 or start_day == 6:
                    days_to_subtract = start_day-4
                    adj_start_date = start_date - pd.Timedelta(str(days_to_subtract)+' days')

            nyse = mcal.get_calendar('NYSE')
            sch = nyse.schedule(start_date = adj_start_date, end_date = adj_end_date)
            indx = mcal.date_range(sch, frequency='1D')

            cleaned_dates = []
            for date in indx:
                clean_date = pd.Timestamp(str(date.month)+'/'+str(date.day)+'/'+str(date.year), tz = 'UTC')
                cleaned_dates.append(clean_date)
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)

            ilist = []
            for i in range(len(cleaned_dates)):
                if i > 0:
                    prev_val = cleaned_dates.month[i-1]
                    cur_val = cleaned_dates.month[i]
                    if cur_val != prev_val:
                        ilist.append(i-1)
            ilist.append(i)
            
            cleaned_dates = cleaned_dates[ilist]
            cleaned_dates = pd.DatetimeIndex(cleaned_dates)

            paired_dates = pd.Series(cleaned_dates,index = data_df.index.unique())

            new_index = pd.DatetimeIndex([paired_dates[date] for date in data_df.index])
            data_df.index = new_index
            

        sym_list = data_df.symbol.unique()
        i = 0
        print('constructing data series')
        for sym in tqdm(sym_list):
            if i == 1:
                sym_data = data_df.loc[data_df.loc[:,'symbol']==sym,:]
                open_series = open_series.append(pd.Series([sym_data.open],index = [sym]))
                high_series = high_series.append(pd.Series([sym_data.high],index = [sym]))
                low_series = low_series.append(pd.Series([sym_data.low],index = [sym]))
                close_series = close_series.append(pd.Series([sym_data.close],index = [sym]))
                volume_series = volume_series.append(pd.Series([sym_data.volume],index = [sym]))
            elif i == 0:
                sym_data = data_df.loc[data_df.loc[:,'symbol']==sym,:]
                open_series = pd.Series([sym_data.open],index = [sym])
                high_series = pd.Series([sym_data.high],index = [sym])
                low_series = pd.Series([sym_data.low],index = [sym])
                close_series = pd.Series([sym_data.close],index = [sym])
                volume_series = pd.Series([sym_data.volume],index = [sym])
                i = 1

        self.open_series = open_series
        self.high_series = high_series
        self.low_series = low_series
        self.close_series = close_series
        self.volume_series = volume_series
        self._bars_to_load = bars_to_load
        self.data_start_date = start_date
        self.strategy_start_date = cleaned_dates[bars_to_load-1]
        self.data_end_date = self.strategy_end_date= cleaned_dates[-1]
        self.sym_list = sym_list
        self.date_index = cleaned_dates

    def load_data_from_excel(self,path,bars_to_load,freq):
        data_df = pd.read_excel(path,index_col = 'date')
        self._adjust_dates_and_transform_data(data_df,bars_to_load,freq)
        
    def load_data_from_csv(self,path,bars_to_load,freq):
        data_df = pd.read_csv(path)
        data_df.index = data_df.date
        self._adjust_dates_and_transform_data(data_df,bars_to_load,freq)
        
    def load_data_from_hdf(self,path,key,bars_to_load,freq):
        data_df = pd.read_hdf(path,key)
        data_df.index.name = 'date'
        data_df.index = pd.to_datetime(data_df.index)
        self._adjust_dates_and_transform_data(data_df,bars_to_load,freq)
    
    def load_data_from_dataframe(self,dataframe,bars_to_load,freq):
        data_df = dataframe
        self._adjust_dates_and_transform_data(data_df,bars_to_load,freq)

class Backtest:

    def __init__(self,strategy = Strategy,portfolio = Portfolio,
                 execution = Execution, datahandler = DataHandler,
                 analysis = Analysis, optimize = Optimize, account = Account):

        self.strategy = strategy()
        self.portfolio = portfolio()
        self.execution = execution()
        self.datahandler = datahandler()
        self.analysis = analysis()
        self.account = account()

        self.strategy._create_pointers(self)
        self.portfolio._create_pointers(self)
        self.datahandler._create_pointers(self)
        self.execution._create_pointers(self)
        self.analysis._create_pointers(self)
        self.account._create_pointers(self)

    def test_strategy(self,cash = 100000):
        self.datahandler._create_date_iter()

        self.account._reset_account(cash)
        
        self.execution._clear_pending_orders()

        self.execution.order_series = pd.Series([('No orders',) for x in range(len(self.datahandler.date_index))], index = self.datahandler.date_index)
        
        self.execution.pending_order_series = pd.Series([('No pending orders',) for x in range(len(self.datahandler.date_index))],index = self.datahandler.date_index)

        for i in tqdm(range(len(self.datahandler.date_index))):
            self.datahandler._update_date_symbols() #updates the current date and list of available symbols
            self.account._remove_delisted_securities()
            self.datahandler._update_begin_bar_data() #updates only open data for current date, allows for begin of bar trading
            self.account._update_account_begin()
            if self.datahandler.current_date>self.datahandler.strategy_start_date:
                self.execution._scan_and_execute_pending_orders()
                self.strategy.strategy_logic_begin()
                self.execution._scan_and_execute_pending_orders()
            self.datahandler._update_end_bar_data()
            self.account._update_account_end()
            if self.datahandler.current_date>self.datahandler.strategy_start_date: #think about implications of > vs >=
                self.execution._scan_and_execute_pending_orders()
                self.strategy.strategy_logic_end()
                self.execution._scan_and_execute_pending_orders()
            self.account._update_account_history_and_results()
            self.analysis.analyze()

    def _optimize_strategy(self,val1,val2,cash = 100000):

        self.datahandler._create_date_iter()

        self.portfolio._reset_portfolio(cash)

        self.strategy.signal_series = pd.Series([('No signals',) for x in range(len(self.datahandler.data_series[0]))])
        self.strategy.signal_series.index = self.datahandler.data_series[0].index

        self.execution.order_series = pd.Series([('No orders',) for x in range(len(self.datahandler.data_series[0]))])
        self.execution.order_series.index = self.datahandler.data_series[0].index

        for i in range(len(self.datahandler.data_series[0])):
            self.datahandler._data_feed() #updates self.datahandler.data
            self.portfolio._update_portfolio()
            if self.datahandler._bars_to_load == len(self.datahandler.data[0]):
                self.strategy.strategy_logic(val1,val2)
            self.portfolio._update_portfolio()
            self.analysis.analyze()