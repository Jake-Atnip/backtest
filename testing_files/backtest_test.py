'''Author: Jacob Atnip'''
import pandas as pd
from copy import deepcopy
from tqdm import tqdm

class Optimize:

    '''Helps run optimations for strategies'''

    def create_optimization_table(self,par1,par1_range,par2,par2_range,strat_name,data_file_path,cash):

        ###This method needs further testing before reliable use###

        '''Creates 3 tables: A CAGR table, Max Drawdown (MDD) table, and a CAGR/MDD table. The row of each table
        represents a value for the first parameter and each column represents a value for the second parameter.
        Values in the CAGR table represent the CAGR for a strategy with that particular combination of values for
        parameter 1 and parameter 2

        Inputs:

        par1 (string): name of the first parameter
        par1_range (range object): range of values to test for parameter 1
        par2 (string): name of the seconf parameter
        par2_range (range object): range of values to test for parameter 2
        strat_name (string): name of strategy
        data_file_path (file path): file path for data to test on
        cash (float): amount of cash to start backtest with'''
        
        #determines number of data points to load for each point in time during the backtest
        bars_to_load = max(max(par1_range),max(par2_range))+1

        #Creates the optimation tables using passed values
        self.optimization_table_max_drawdown = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_max_drawdown.index.name = str(par1)
        self.optimization_table_max_drawdown.columns.name = str(par2)

        self.optimization_table_CAGR = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_CAGR.index.name = str(par1)
        self.optimization_table_CAGR.columns.name = str(par2)

        self.optimization_table_CAGRMDD = pd.DataFrame(0,index = par1_range,columns = par2_range)
        self.optimization_table_CAGRMDD.index.name = str(par1)
        self.optimization_table_CAGRMDD.columns.name = str(par2)

        #Determines number of backtests required
        no_of_iterations = len(par1_range)*len(par2_range)
        q = 1

        #Runs the backtests and fills in the table
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

    '''Houses all methods for calculating metrics used to evaluate strategy performance'''

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.account = backtest.account
        self.backtest = backtest

    def analyze(self):

        '''Create an analysis class that inherits from this class and create an analyze function where you 
        write any metric you want to keep track of during the backtest'''

        pass

    def _create_underwater_plot(self):
        #Creates underwater plot of results
        underwater_plot = self.account.account_results.loc[:,['value']]
        underwater_plot.loc[:,'max'] = 0
        for i in range(len(self.portfolio.results)):
            max_val = self.portfolio.results.iloc[0:i,0].max()
            underwater_plot.iloc[i-1,1] = max_val
        underwater_plot.iloc[-1,1] = underwater_plot.iloc[:,0].max()
        self.underwater_plot = underwater_plot

    def _calc_drawdown(self):
        #calculaes the max drawdown from the under water plot
        self._create_underwater_plot()
        self.drawdown_df = -(1-(self.underwater_plot.loc[:,'portfolio value']/self.underwater_plot.loc[:,'max']))
        self.max_drawdown = self.drawdown_df.min()

    def _calc_CAGR(self):
        #Calculuates the CAGR
        end_val = self.account.account_results.loc[self.datahandler.strategy_end_date,'value']##fix this###
        start_val = self.account.account_results.loc[self.datahandler.strategy_start_date,'value']
        no_of_years = (self.account.account_results.index[-1] - self.account.account_results.index[0]).days/365
        self.CAGR = ((end_val/start_val)**(1/no_of_years))-1

    def _calc_CAGRMDD(self):
        ###Calculates the CAGR/MDD metric
        self._calc_drawdown()
        self._calc_CAGR()
        self.CAGRMDD = -(self.CAGR/self.max_drawdown)


    def results_overview(self):

        '''This method will provide a tearsheet showing the overview of the results of a backtest'''

        pass

class Strategy:

    '''This class contains the methods for beginning of bar logic and end of bar logic
    Create your own strategy class that inherits from this class'''

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def strategy_logic_begin(self):

        '''Code your beginning of bar logic here (if your strategy requires)'''

        print('Make sure to add the parameter strategy = yourstrategyname when creating an instance of the Backtest class')
    
    def strategy_logic_end(self):

        '''Code your end of bar logic here (if your strategy requires)'''

        print('Make sure to add the parameter strategy = yourstrategyname when creating an instance of the Backtest class')
        
class Account:

    '''This class contains methods for handling delisted securities, updating the account, changing the account in response to orders,
    and updating account history'''
    
    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.analysis = backtest.analysis
        self.strategy = backtest.strategy
        self.backtest = backtest
        
    def _reset_account(self, cash = 100000):
        #Creates an assets, liabilities, and equity dictionary. Creates two dataframe: account history and account results dataframe
        self.assets = {'cash':cash}
        self.liabilities = {'borrowed funds':0}
        self.equity = {'account value':cash}
        self.account_history = pd.DataFrame({'assets':[() for i in self.datahandler.date_index],'liabilities':[() for i in self.datahandler.date_index],'equity':[() for i in self.datahandler.date_index]},index = self.datahandler.date_index)
        self.account_history.iloc[0,0] = (deepcopy(self.assets),)
        self.account_history.iloc[0,1] = (deepcopy(self.liabilities),)
        self.account_history.iloc[0,2] = (deepcopy(self.equity),)
        self.account_results = pd.DataFrame({'cash':[() for i in self.datahandler.date_index],'value':[() for i in self.datahandler.date_index]},index = self.datahandler.date_index)

    def _remove_delisted_securities(self):
        #Handles the removal of delisted securities each bar
        #First handles securities that are owned and have been deslited
        del_list1 = []
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

        #Then removes securities that are shorted (liabilities) and have been delisted
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

        #Removes any delisted securities from pending order 
        pending_orders = [order for order in self.execution.pending_orders if self.execution.pending_orders[order]['symbol'] in del_list1 or self.execution.pending_orders[order]['symbol'] in del_list2]
        for order in pending_orders:
            del self.execution.pending_orders[order]
            

    def _update_account_begin(self):
        #Updates the account at the beginning of the current bar

        values = []
        #update asset values
        for asset in self.assets:
            if asset != 'cash':
                asset_data = self.assets[asset]
                asset_data['value'] = asset_data['quantity']*self.datahandler._data_series[asset]['open'][self.datahandler.current_date]
                values.append(asset_data['value'])
                self.assets[asset].update(asset_data)

        #update liability values
        for liability in self.liabilities:
            if liability != 'borrowed funds':
                liability_data = self.liabilities[liability]
                liability_data['value'] = liability_data['quantity']*self.datahandler._data_series[liability]['open'][self.datahandler.current_date]
                values.append(-liability_data['value'])
                self.liabilities[liability].update(liability_data)

        #update equity values
        self.equity['account value'] = sum(values)+self.assets['cash']-self.liabilities['borrowed funds']
        
        #Update the portfolio.positions tuple
        self.portfolio.positions = [asset for asset in self.assets if asset != 'cash']
        self.portfolio.positions = self.portfolio.positions + [liability for liability in self.liabilities if liability != 'borrowed funds']
        self.portfolio.positions = tuple(self.portfolio.positions)

    def _update_account_end(self):
        #Updates the account at the end of the current bar

        values = []

        #updates asset values
        for asset in self.assets:
            if asset != 'cash':
                asset_data = self.assets[asset]
                asset_data['value'] = asset_data['quantity']*self.datahandler._data_series[asset]['close'][self.datahandler.current_date]
                values.append(asset_data['value'])
                self.assets[asset].update(asset_data)

        #updates the value of liabilities
        for liability in self.liabilities:
            if liability != 'borrowed funds':
                liability_data = self.liabilities[liability]
                liability_data['value'] = liability_data['quantity']*self.datahandler._data_series[liability]['close'][self.datahandler.current_date]
                values.append(-liability_data['value'])
                self.liabilities[liability].update(liability_data)

        #updates equity value
        self.equity['account value'] = sum(values)+self.assets['cash']-self.liabilities['borrowed funds']
        
        #updates the portfolio positions tuple
        self.portfolio.positions = [asset for asset in self.assets if asset != 'cash']
        self.portfolio.positions = self.portfolio.positions + [liability for liability in self.liabilities if liability != 'borrowed funds']
        self.portfolio.positions = tuple(self.portfolio.positions)
        
    def _update_account_history_and_results(self):
        #updates the account history and account results dataframes

        self.account_history['assets'][self.datahandler.current_date] = deepcopy(self.assets)
        self.account_history['liabilities'][self.datahandler.current_date] = deepcopy(self.liabilities)
        self.account_history['equity'][self.datahandler.current_date] = deepcopy(self.equity)
        self.account_results['cash'][self.datahandler.current_date] = self.assets['cash']
        self.account_results['value'][self.datahandler.current_date] = self.equity['account value']

    def _calculate_change_cost_basis_and_new_ladder_FIFO(self,shares,ladder):
        #Updates the cost basis and position ladder using the FIFO method

        share_count = 0
        cost = 0
        change = 0

        ###Needs additional documentation here###
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
        #Updates the account whenever an order is executed

        if order['symbol'] not in self.assets and order['symbol'] not in self.liabilities:
            #There is not a position open for this symbol

            if order['quantity'] >0:
                #order creates a long position

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

                #determine whether position is bought with cash or a mixture of cash and borrowed funds
                if value <= self.assets['cash']:
                    self.assets['cash'] = self.assets['cash'] - value
                else:
                    self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+(value - self.assets['cash'])
                    self.assets['cash'] = 0

                #add position to assets account 
                self.assets[order['symbol']] = pos_dict

            #Creates position dictionary for short positio
            elif order['quantity'] < 0:
                #order creates a short position

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

                #Updates cash account and liabilities account
                self.assets['cash'] = self.assets['cash']+value
                self.liabilities[order['symbol']] = pos_dict

        else:
            #There is a current position open for this symbol
            if order['symbol'] in self.assets:
                #there is a long position for this symbol

                if order['quantity'] + self.assets[order['symbol']]['quantity'] > 0:
                    #current order still maintains long position

                    quantity = abs(order['quantity'] + self.assets[order['symbol']]['quantity'])
                    value = quantity*order['execution price']
                    if order['quantity'] > 0:
                        #order creates larger long position
                        cost_basis = abs(order['quantity'])*order['execution price'] + self.assets[order['symbol']]['cost basis']
                        ladder = self.assets[order['symbol']]['ladder'] + [(abs(order['quantity']),order['execution price'])]

                        if (order['quantity']*order['execution price']) <= self.assets['cash']:
                            #order uses only cash
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                        else:
                            #order will use borrowed funds 
                            self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                            self.assets['cash'] = 0

                    else:
                        #order decreases the size of the long position
                        cost_basis_change,ladder = self._calculate_change_cost_basis_and_new_ladder_FIFO(abs(order['quantity']),self.assets[order['symbol']]['ladder'])
                        cost_basis = self.assets[order['symbol']]['cost basis'] - cost_basis_change

                        if (abs(order['quantity'])*order['execution price']) >= self.liabilities['borrowed funds']:
                            #order completely pays back borrowed funds
                            self.assets['cash'] = self.assets['cash']+((abs(order['quantity'])*order['execution price']) - self.liabilities['borrowed funds'])
                            self.liabilities['borrowed funds'] = 0
                        else:
                            #order does not completely pay back borrowed funds
                            self.liabilities['borrowed funds'] = self.liabilities['borrowed funds'] - ((abs(order['quantity'])*order['execution price']))

                    #finishes constructing the position dictionary
                    pos_dict = {'value':value,
                    'quantity':quantity,
                    'most recent order':order,
                    'cost basis':cost_basis,
                    'ladder':ladder}

                    #updates the asset account with the new position dictionary
                    self.assets[order['symbol']].update(pos_dict)

                elif order['quantity'] + self.assets[order['symbol']]['quantity'] <0:
                    #current order changes the long position to a short position

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
                        #order pays back all of the current borrowed funds
                        self.assets['cash'] = self.assets['cash'] + ((self.assets[order['symbol']]['quantity']*order['execution price']) - self.liabilities['borrowed funds']) + (quantity*order['execution price'])
                        self.liabilities['borrowed funds'] = 0
                    else:
                        #order does not pay back all of the current borrowed funds
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds'] - (self.assets[order['symbol']]['quantity']*order['execution price'])
                        #cash from short positions is placed in cash account and not used to pay back borrowed funds
                        ###Check to see if this is the correct logic###
                        self.assets['cash'] = self.assets['cash'] + quantity*order['execution price']

                    #removes the position from the assets and adds the new short position to the liabilities account
                    del self.assets[order['symbol']]
                    self.liabilities[order['symbol']] = pos_dict


                elif (order['quantity'] + self.assets[order['symbol']]['quantity'])==0:
                    #order closes the long position

                    if (abs(order['quantity'])*order['execution price']) >= self.liabilities['borrowed funds']:
                            #order completely pays back borrowed funds
                        self.assets['cash'] = self.assets['cash']+((abs(order['quantity'])*order['execution price']) - self.liabilities['borrowed funds'])
                        self.liabilities['borrowed funds'] = 0
                    else:
                        #order does not completely pay back borrowed funds
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds'] - ((abs(order['quantity'])*order['execution price']))
                    
                    #removes the symbol from the asset account
                    del self.assets[order['symbol']]

            elif order['symbol'] in self.liabilities:
                #there is a short position for this symbol

                if order['quantity'] + (-self.liabilities[order['symbol']]['quantity']) > 0:
                    #order changes the short position to a long position

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
                        #order uses only cash to fund purchase
                        self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                    else:
                        #order uses borrowed funds to purchase
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                        self.assets['cash'] = 0

                    #removes the symbol from liabilities and adds it to the assets
                    del self.liabilities[order['symbol']]
                    self.assets[order['symbol']] = pos_dict


                elif order['quantity'] + (-self.liabilities[order['symbol']]['quantity']) <0:
                    #current order maintains short position

                    quantity = abs(order['quantity'] + (-self.liabilities[order['symbol']]['quantity']))
                    value = quantity*order['execution price']
                    if order['quantity'] > 0:
                        #current order reduces the size of the short position
                        cost_basis_change,ladder = self._calculate_change_cost_basis_and_new_ladder_FIFO(abs(order['quantity']),self.liabilities[order['symbol']]['ladder'])
                        cost_basis = self.liabilities[order['symbol']]['cost basis'] - cost_basis_change
                        if (order['quantity']*order['execution price']) <= self.assets['cash']:
                            #order uses only cash for purchase
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                        else:
                            #order uses borrowed funds for purchase
                            self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                            self.assets['cash'] = 0
                        
                    else:
                        #order increases size of short position
                        cost_basis = abs(order['quantity'])*order['execution price'] + self.liabilities[order['symbol']]['cost basis']
                        ladder = self.liabilities[order['symbol']]['ladder'] + [(abs(order['quantity']),order['execution price'])]
                        self.assets['cash'] = self.assets['cash']+abs(order['quantity'])*order['execution price']

                    #updates position dictionary
                    pos_dict = {'value':value,
                    'quantity':quantity,
                    'most recent order':order,
                    'cost basis':cost_basis,
                    'ladder':ladder}

                    #updates the liabilities account
                    self.liabilities[order['symbol']].update(pos_dict)

                elif order['quantity'] + (-self.liabilities[order['symbol']]['quantity'])==0:
                    #order closes the short position

                    if (order['quantity']*order['execution price']) <= self.assets['cash']:
                        #order uses only cash to close short
                            self.assets['cash'] = self.assets['cash'] - (order['quantity']*order['execution price'])

                    else:
                        #order uses borrowed funds to close short
                        ###Is this the correct logic?###
                        self.liabilities['borrowed funds'] = self.liabilities['borrowed funds']+((order['quantity']*order['execution price']) - self.assets['cash'])
                        self.assets['cash'] = 0

                    #removes order from the liabilities account
                    del self.liabilities[order['symbol']]

class Portfolio:

    '''This class contains the positions tuple and a method for resetting this tuple at the beginning of each backtest'''

    def _create_pointers(self,backtest):
        self.execution = backtest.execution
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def _reset_portfolio(self):
        #resets portfolio
        self.positions = ()
            
class Execution:

    '''This class handles all methods and data related to pending and executing orders'''

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.datahandler = backtest.datahandler
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest
    
    def _clear_pending_orders(self):
        #resets pending orders dict and the most recent order ID
        self.pending_orders = {}
        self._most_recent_ID = 0
        
    def _add_pending_order(self,order):
        #adds an order to the pending orders dictionary
        order_ID = order['Order ID']
        self.pending_orders[order_ID] = deepcopy(order)
            
    def _execute_order(self,order):
        #executes order by updating the account with an order
        self.account._update_account_with_order(order)
                
    def _scan_and_execute_pending_orders(self):
        #scans the pending orders dict and executes order if necessary

        #list used to keep track of orders that need to be removed from pending list
        removal_list = []
        for ID in self.pending_orders:
            order = self.pending_orders[ID]
            order_type = order['order type']
            
            if order_type == 'market':
                market_order_type = order['desired execution time']
                if market_order_type == 'open':
                    if self.datahandler._tob == 'begin':
                        #chain of if/else statements ensure the market order is only executed at the beginning of the bar
                        sym = order['symbol']
                        sym_open_data = self.datahandler._data_series[sym]['open']
                        execution_price = sym_open_data[self.datahandler.current_date]
                        order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'begin'})
                        self._update_order_series(order)
                        self._execute_order(order)
                        removal_list.append(ID)
                elif market_order_type == 'close':
                    if self.datahandler._tob == 'end':
                        #chain of if/else statements ensure the market order is only executed at the end of the bar
                        sym = order['symbol']
                        sym_close_data = self.datahandler._data_series[sym]['close']
                        execution_price = sym_close_data[self.datahandler.current_date]
                        order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'end'})
                        self._update_order_series(order)
                        self._execute_order(order)
                        removal_list.append(ID)

        #removes pending orders that have been executed
        self._update_pending_orders(removal_list)
        
    def _update_pending_orders(self,removal_list):
        #removes pending orders that have been executed
        for ID in removal_list:
            del self.pending_orders[ID]

    def _gen_order_ID(self):
        #generates a new order ID. All order IDs are unique
        ID = self._most_recent_ID
        self._most_recent_ID += 1
        return ID

    def _update_order_series(self,order):
        #updates new order series

        if self.order_series.loc[self.datahandler.current_date] != ('No orders',):
            self.order_series.loc[self.datahandler.current_date] = (self.order_series.loc[self.datahandler.current_date] +(order,))

        elif self.order_series.loc[self.datahandler.current_date] == ('No orders',):
            self.order_series.loc[self.datahandler.current_date] = (order,)

    def _update_pending_order_series(self,order):
        #updates the pending order series

        if self.pending_order_series.loc[self.datahandler.current_date] != ('No pending orders',):
            self.pending_order_series.loc[self.datahandler.current_date] = (self.pending_order_series.loc[self.datahandler.current_date] +(order,))

        elif self.pending_order_series.loc[self.datahandler.current_date] == ('No pending orders',):
            self.pending_order_series.loc[self.datahandler.current_date] = (order,)

    def market_order(self,symbol,quantity,time):

        '''This method is responsible for generating an order dict for a market order

        inputs:
        symbol (string): symbol (stock ticker, forex pari, etc.)
        quantity (int): units of symbol to order. Use positive (negative) values for long (short) positions or covering (closing) short (long) positions.
        time (string): 'begin' or 'end', determines time of bar the order should be executed'''

        ID = self._gen_order_ID()

        #creates new order dict
        order = {'Order ID': ID,
        'date of placement':self.datahandler.current_date,
        'time of placement':self.datahandler._tob,
        'order type':'market',
        'symbol':symbol,
        'quantity':quantity,
        'desired execution time':time}

        #adds order to the pending order series. This is not the pending order dict. This is for history purposes
        self._update_pending_order_series(order)
        
        #If/else chain handles whether order should be executed immediately or placed into the pending order dict
        if order['desired execution time'] == 'open':
            if order['time of placement'] == 'begin':
                sym = order['symbol']
                sym_open_data = self.datahandler._data_series[sym]['open']
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
                sym_close_data = self.datahandler._data_series[sym]['close']
                execution_price = sym_close_data.loc[self.datahandler.current_date]
                order.update({'execution price':execution_price, 'date of execution':self.datahandler.current_date,'execution side':'end'})
                self._update_order_series(order)
                self._execute_order(order)
                
            elif order['time of placement'] == 'begin':
                self._update_pending_order_series(order)
                most_recent_order = (self.pending_order_series.loc[self.datahandler.current_date])[-1]
                self._add_pending_order(most_recent_order)

class DataHandler:

    '''This class houses all methods used for adding data series before the backtest and 
    updating data series during the backtest'''

    def __init__(self):
        #creates lists used for determining what time of bar a data series should be updated
        self.begin_data_list = []
        self.end_data_list = []

        self.begin_data_series_list = []
        self.end_data_series_list = []

    def _create_pointers(self,backtest):
        self.portfolio = backtest.portfolio
        self.execution = backtest.execution
        self.strategy = backtest.strategy
        self.analysis = backtest.analysis
        self.account = backtest.account
        self.backtest = backtest

    def _create_date_iter(self,bars_to_load):
        #creates bars to load variable, creates date iter object, and creates the tob (time of bar) variable
        self._bars_to_load = bars_to_load
        self._date_iter = iter(self.date_index)
        self._tob = 'end'

    def _update_time(self):
        if self._tob == 'end':
            self._tob = 'begin'
        else:
            self._tob = 'end'

    def _update_date_symbols(self):
        #updates the current date and generates a list of symbols available for that date
        self.current_date = next(self._date_iter)
        if self.current_date >= self.strategy_start_date:
            self.available_symbols = []
            for sym in self.sym_list:
                if self.current_date in self._data_series[sym].index:
                    ###Find a less time consuming way to do this###
                    temp_df = self._data_series[sym]
                    amount_of_data = len(temp_df.index[temp_df.index <= self.current_date])
                    if amount_of_data >=self._bars_to_load:
                        self.available_symbols.append(sym)
            self.available_symbols = tuple(self.available_symbols)

    def add_data_series(self,series,beginning_update_list = []):

        '''This method is used for adding data series before the backtest. You must run this method twice: 
        once to add the open_series and another time to add the close_series

        inputs:
        series_name (string): name of the series, should have the format 'nameofseries_series'
        series (pandas series): pandas series containing data. Index of this series is the symbols and each value
            in the series is another pandas series with a date index and containing data for that particular symbol
        time_to_update (string): must have value 'begin' or 'end'. Default is 'end'. Determines what time of bar this data 
        series will be updated'''

        if 'open' not in beginning_update_list:
            beginning_update_list.append('open')

        self._beginning_update_list = beginning_update_list

        self._data_series = series

        #creates symbol list, start date, end date, and date index variables from the close series
        self.strategy_start_date = min([series.index[0] for series in self._data_series])
        self.strategy_end_date = max([series.index[-1] for series in self._data_series])
        self.sym_list = list(self._data_series.index)
        self.date_index = pd.Index([])
        for dataframe in self._data_series:
            self.date_index = self.date_index.append(dataframe.index)
        self.date_index = self.date_index.unique()

    def data(self,symbol,data_type,number_of_bars):
        if number_of_bars > self._bars_to_load:
            raise ValueError('number_of_bars exceeds the specified bars to load')

        temp_slice = self._data_series[symbol][data_type]
        current_date_location = temp_slice.index.get_loc(self.current_date)
        start_location = current_date_location+1-number_of_bars
        if self._tob == 'begin' and data_type in self._beginning_update_list:
            temp_slice = temp_slice[start_location:current_date_location+1]
        elif self._tob == 'begin' and data_type not in self._beginning_update_list:
            temp_slice = temp_slice[start_location-1:current_date_location]
        elif self._tob == 'end':
            temp_slice = temp_slice[start_location:current_date_location+1]
        return temp_slice

class Backtest:

    '''This class contains the main loop of the backtester and is used to start the backtest'''

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

    def test_strategy(self,bars_to_load,cash = 100000):

        '''tests the strategy

        inputs:
        bars_to_load (int): number of data bars to load at a time during the backtest. Usually the amount of data required for the longest indicator
        cash (float): amount of cash to start the test with. Default is 100,000'''

        #creates the date iter object        
        self.datahandler._create_date_iter(bars_to_load)

        #resets the account
        self.account._reset_account(cash)
        
        #clears any pending orders
        self.execution._clear_pending_orders()

        #creates execution order series for history purposes
        self.execution.order_series = pd.Series([('No orders',) for x in range(len(self.datahandler.date_index))], index = self.datahandler.date_index)
        
        #creates execution pending order series for history purposes
        self.execution.pending_order_series = pd.Series([('No pending orders',) for x in range(len(self.datahandler.date_index))],index = self.datahandler.date_index)

        #main loop of backtester
        ###Improve this with an apply method###
        for i in tqdm(range(len(self.datahandler.date_index))):
            #updates the current date and list of available symbols
            self.datahandler._update_date_symbols() 
            #removes delisted securities from account and pending orders
            self.account._remove_delisted_securities()
            #updates data series at beginning of bar
            self.datahandler._update_time()
            #updates the account to reflect new data
            self.account._update_account_begin()
            if self.datahandler.current_date>self.datahandler.strategy_start_date:
                #current date is past strategy start date so the strategy has enough data to begin
                #executes pending orders if necessary
                self.execution._scan_and_execute_pending_orders()
                #executes logic at the beginning of bar
                self.strategy.strategy_logic_begin()
                #executes pending orders if necessary
                self.execution._scan_and_execute_pending_orders()
            #updates data series at end of bar
            self.datahandler._update_time()
            #updates account to reflect new data
            self.account._update_account_end()
            if self.datahandler.current_date>self.datahandler.strategy_start_date: ####think about implications of > vs >=###
                #executes pending orders if necessary
                self.execution._scan_and_execute_pending_orders()
                #executes strategy logic at end of bar
                self.strategy.strategy_logic_end()
                #executes pending orders if necessary
                self.execution._scan_and_execute_pending_orders()
            #updates the account history and results dataframes
            self.account._update_account_history_and_results()
            #runs the analyze function is there is data or metrics that the user wants to calculate/log
            self.analysis.analyze()

    def _optimize_strategy(self,bars_to_load, val1,val2,cash = 100000):

        '''Has not been fully tested'''

        self.datahandler._create_date_iter(bars_to_load)

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