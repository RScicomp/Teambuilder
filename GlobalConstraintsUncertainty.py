import pandas as pd
from pulp import *
import numpy as np

#Include possibility of payback of salary
UNCERTAINTY = True
#Include all players
ALLPLAYERS = True
#Adjust budget
BUDGET=109.14 *10**6
#Four factors
fourfactorconstr=.1
#Age constraint
AGECONSTRAINT=50
#Max forward injuries
MAXFINJ = 100
#Max Center injuries
MAXCINJ = 100
#Max Guard injuries
MAXGINJ= 100
#Max centers
MAXC= 4
#Max guards
MAXG=10
#Max forwards
MAXF=10


def showresults(prob):
    # The status of the solution is printed to the screen
    print("="*30,"\nSolution Status:", LpStatus[prob.status])

    # Results
    obj = value(prob.objective)
    print("The objectve is {}".format(round(obj,2)))

    print("Optimal Solution:")
    for v in prob.variables():
        if(v.varValue==1):
            print(v.name, "=", v.varValue)

    print("Constraints")
    for c in list(prob.constraints.values()):
        print(c.name, "=", c.value())
        
def sensitivity(prob):
    #Print reduced costs
    o = [{'Variables':v.name,
          'Final Value':v.varValue,
          'Reduced Cost':v.dj,
          }
         for v in prob.variables()]
    print(pd.DataFrame(o),'\n')

    #Print shadow price and constraint slack
    o = [{'Constraint':name,
          'Shadow Price':c.pi,
          'RHS':-c.constant,
          'Slack': c.slack}
         for name, c in prob.constraints.items()]
    print(pd.DataFrame(o))
    
    

    
    
    
    
free_agents=pd.read_csv("free_agents.csv")
raptors=pd.read_csv("raptors.csv")
raptors.rename(columns={'name': 'Player','free agent': 'raptors free agent'},inplace=True, errors='raise')
raptors['Raptors']=True
free_agents= free_agents[free_agents['Player'].isin(raptors['Player'])==False].reset_index(drop=True)

salaries=pd.read_excel("salaries.xlsx")
allplayers2019=pd.read_csv("2019_players_all.csv")
allplayers2019=pd.merge(allplayers2019,salaries,left_on="Player",right_on="PLAYER",how="left")
allplayers2019=allplayers2019.dropna().reset_index(drop=True)
allplayers2019.drop(list(allplayers2019.columns[allplayers2019.columns.str.contains("_y")]),axis=1)
allplayers2019.rename(columns={'2019/20': 'AVG SALARY'},inplace=True, errors='raise')
allplayers2019=allplayers2019[(allplayers2019['Player'].isin(raptors['Player'])==False)&(allplayers2019['Player'].isin(free_agents['Player'])==False)].reset_index(drop=True)
allplayers2019['free agent']=0

free_agents['free agent']=1
if(ALLPLAYERS==True):
    free_agents=free_agents.append(allplayers2019).reset_index(drop=True)

free_agents=free_agents.append(raptors).reset_index(drop=True)
free_agents=free_agents[free_agents['MP'] >= 100].reset_index(drop=True)
free_agents=free_agents[free_agents['AVG SALARY'] != '-'].reset_index(drop=True)


injuries=pd.read_csv("injuries_2010-2020.csv")
injuries=injuries[injuries['Relinquished'].isin(free_agents['Player'])]
injuries=injuries.groupby("Relinquished").count()
injuries=injuries[injuries.columns[0:1]]
injuries.columns=["injuries"]
free_agents=pd.merge(free_agents,injuries,left_on="Player",right_on="Relinquished",how="left")





### Turn non-percentage values to percentages ------------------------------------------------------------------------------------
percentages=free_agents.columns[free_agents.columns.str.contains("%")]
res=[free_agents[percentage]/100 if len(free_agents[free_agents[percentage]>1])>1 else free_agents[percentage] for percentage in percentages]

res=pd.DataFrame(res).T
for col in list(res.columns):
    free_agents[col]=res[col]
    
free_agents['eFG']= (free_agents['FG'] + 0.5 * free_agents['3P'])/ free_agents['FGA']
free_agents['TOV_Factor']=free_agents['TOV'] / (free_agents['FGA']+ 0.44 * free_agents['FTA']+ free_agents['TOV']) 
free_agents = free_agents.replace(np.nan, 0)


typeplayer= list(set(free_agents['TYPE']))
positions= list(set(free_agents['Pos']))

playersall = LpVariable.dicts(name='Agent', indexs=range(len(free_agents)), cat=LpBinary) 
playertypes= LpVariable.dicts(name="Player",indexs=(range(15),positions),cat=LpBinary) # Ensure that player has 
nonfree=free_agents[(free_agents['raptors free agent']==0)&(free_agents['Raptors']==True)]
raptornonfreeagentsold=LpVariable.dicts(name='Raptors_NonAgent', indexs=nonfree.index, cat=LpBinary) 
positions = LpVariable.dicts(name='Position', indexs=positions, cat=LpBinary) # Ensure all positions are filled

from scipy import stats
nonfree['chance_of_recouping']=""
for agent in nonfree.index:
    #samepos=free_agents[free_agents['Pos']==free_agents['Pos'][list(transcostsnonfree_recoup.keys())][agent]]
    #print(len(samepos))
    #if(len(samepos)>1):
    winshareagent=free_agents['WS'][agent]
    nonfree['chance_of_recouping'][agent]=stats.percentileofscore(free_agents['WS'], winshareagent, kind='rank')/100

    
    
    
    
### Objective Four Factors + WS ------------------------------------------------------------------------------------------------
eFG=lpSum(np.array(free_agents['eFG'])*np.array(list(playersall.values())))
TOV_Factor=lpSum(np.array(free_agents['TOV_Factor'])*np.array(list(playersall.values())))
ORB=lpSum(np.array(free_agents['ORB%'])*np.array(list(playersall.values())))
DRB=lpSum(np.array(free_agents['DRB%'])*np.array(list(playersall.values())))




playersbought=15

prob = LpProblem("NBA")
prob.sense = LpMaximize

#divide by playersbought for gurobi instead of 15?
objectiveWS=lpSum(free_agents['WS']*np.array(list(playersall.values())))
objectiveFF=lpSum((.4*eFG)/playersbought - (.25*TOV_Factor)/playersbought + (.2*ORB)/playersbought + (.15*DRB)/playersbought)
#probfourfactors+=objectivefourfactors
#prob.addConstraint(LpConstraint(name="Secondary Objective",e=secondaryobjective,sense=1,rhs=fourfactorconstr))
#-> include in Notebook








### Global Constraints -----------------------------------------------------------------------------------------------

#ensure that we deduct the salary of non free agents on raptors if we choose to kick them
for i in raptornonfreeagentsold.keys():
    inverse=LpConstraint(name="RaptorsnonAgent_sold"+str(i),e=-1+playersall[i]+raptornonfreeagentsold[i],sense=0,rhs=0) #Constraint that if we keep 1, then this variable must be the inverse 0. Ie no matter what we pay their salary
    prob.addConstraint(inverse)
    
    
    
    
    
    
    
    
#budget constraint:  ------------------------------------------------------------------------------------------------
averagesalary = [int(salary) for salary in free_agents['AVG SALARY'] if salary != "-"]
#Need to fill in NAs
#out of the league if no average salary
minimumsalary = 898310 #[898310,1445697,1620564,1678854,1737145,1882867,2028594,2174318,2320044,2331593,2564753]
free_agents['AVG SALARY'] = [int(salary) if salary != "-" else minimumsalary for salary in free_agents['AVG SALARY']]
##notefinished

#transactioncost=0
#ensure that raptors players that aren't free agents, if kicked, we have to pay their salary
if(UNCERTAINTY == True):
    uncertaintransactioncost= 0
    for i in nonfree.index:
        cost=((1-nonfree['chance_of_recouping'][i])*nonfree['salary_2020'][i]*raptornonfreeagentsold[i])#+((1-nonfree['chance_of_recouping'][i])*nonfree['salary_2020'][i]*raptornonfreeagentsold[i])
        uncertaintransactioncost+=cost


    uncertaintransactioncost=lpSum(uncertaintransactioncost)
    transactioncost=uncertaintransactioncost
else:
    transactioncost=0

    #transactioncost=0
    #ensure that raptors players that aren't free agents, if kicked, we have to pay their salary
    for indexrap in raptornonfreeagentsold.keys():
        transactioncost += raptornonfreeagentsold[indexrap]*free_agents['salary_2020'][indexrap]

    
spending=lpSum(np.array(free_agents['AVG SALARY'])*np.array(list(playersall.values()))+transactioncost)


budgetconstraint=LpConstraint(name="budget_constraint",e=spending,sense=-1,rhs=BUDGET)
prob.addConstraint(budgetconstraint)
 

    
    
    
#Team size must be 15 ------------------------------------------------------------------------------------------------
teamconstraint=LpConstraint(name="team_size",e=lpSum(np.array(list(playersall.values()))),rhs=15,sense=0)
prob.addConstraint(teamconstraint)

### Positional Constraints
def positionalconstraints(df,keyword="C",cname="Center Constraint",constr=2,sense=1):
    centres=df[df['Pos'].str.contains(keyword)]
    subcentres=set(centres['Pos'])
    #does a forward Centre count as two?
    centerconstraint=0
    for center in centres.index:
        centerconstraint+=playersall[center]
    centreconstraint=LpConstraint(name=cname,e=centerconstraint,sense=sense,rhs=constr)
    return(centreconstraint)

### Positional Constraints injuries
def positionalconstraintsinj(df,keyword="C",cname="Center Constraint",constr=2,sense=1):
    centres=df[df['Pos'].str.contains(keyword)]
    subcentres=set(centres['Pos'])
    #does a forward Centre count as two?
    centerconstraint=0
    for center in centres.index:
        centerconstraint+=playersall[center]*df['injuries'][center]
    centreconstraint=LpConstraint(name=cname,e=centerconstraint,sense=sense,rhs=constr)
    return(centreconstraint)


#minimum number of centres, guards, forwards
prob.addConstraint(positionalconstraints(free_agents))
prob.addConstraint(positionalconstraints(free_agents,keyword="G",cname="Guard Constraint",constr=5))
prob.addConstraint(positionalconstraints(free_agents,keyword="F",cname="Forward Constraint",constr=5))

#cap the number of centres, guards, forwards
prob.addConstraint(positionalconstraints(free_agents,cname="Center Constraint Max",sense=-1,constr=MAXC))
prob.addConstraint(positionalconstraints(free_agents,keyword="G",cname="Guard Constraint Max",constr=MAXG,sense=-1))
prob.addConstraint(positionalconstraints(free_agents,keyword="F",cname="Forward Constraint Max",constr=MAXF,sense=-1))

forwardmaxinjuries=positionalconstraintsinj(free_agents,keyword="F",cname="Forward Constraint Inj",constr=MAXFINJ,sense=-1)
centermaxinjuries=positionalconstraintsinj(free_agents,cname="Center Constraint Inj",sense=-1,constr=MAXCINJ)
guardmaxinjuries=positionalconstraintsinj(free_agents,keyword="G",cname="Guard Constraint Inj",constr=MAXGINJ,sense=-1)

prob.addConstraint(forwardmaxinjuries)
prob.addConstraint(centermaxinjuries)
prob.addConstraint(guardmaxinjuries)


### Age Constraint

ages=lpSum(free_agents['Age']*np.array(list(playersall.values()))/15)
ageconstraint=LpConstraint(name="Ageconstraint",e=ages,rhs=AGECONSTRAINT,sense=-1)
prob.addConstraint(ageconstraint)


















