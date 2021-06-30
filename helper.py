import pandas as pd
from pulp import *
import numpy as np

def showresults(prob):
    final="="*30+"\nSolution Status:"+ str(LpStatus[prob.status])

    # The status of the solution is printed to the screen
    
    # Results
    obj = prob.objective.value()
    final="The objectve is {}".format(round(obj,2))
    
    print("Optimal Solution:")
    for v in prob.variables():
        if(v.varValue==1):
            final+="\n"+ str(v.name)+ " = " +  str(v.varValue)

    print("Constraints")
    for c in list(prob.constraints.values()):
        final+="\n"+str(c.name) +"="+str(c.value())
    return(final)
        
def sensitivity(prob):
    #Print reduced costs
    o = [{'Variables':v.name,
          'Final Value':v.varValue,
          'Reduced Cost':v.dj,
          }
         for v in prob.variables()]
    o=pd.DataFrame(o)
    
    #Print shadow price and constraint slack
    p = [{'Constraint':name,
          'Shadow Price':c.pi,
          'RHS':-c.constant,
          'Slack': c.slack}
         for name, c in prob.constraints.items()]
    p=pd.DataFrame(p)
    return(p,o)
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

def positionalconstraintsFF(df,playersall,playersbought=15,feature='TOV_Factor',keyword="C",cname="Center Constraint",constr=2,sense=1):
    centres=df[df['Pos'].str.contains(keyword)]
    subcentres=set(centres['Pos'])
    #does a forward Centre count as two?
    centerconstraint=0
    playerspos=0
    for center in centres.index:
        centerconstraint+=playersall[center]*df[feature][center]
        playerspos+=playersall[center]*1
    rhs=constr*lpSum(playerspos)
#     print("DONE")
#     try:
#         test=LpConstraint(name=cname,e=lpSum(centerconstraint),sense=sense,rhs=rhs)
#     except Exception as e:
#         print("ERROR",e)
#         pass
    centreconstraint=LpConstraint(name=cname,e=lpSum(centerconstraint-rhs),sense=sense,rhs=0)

    #centreconstraint=LpConstraint(name=cname,e=lpSum(centerconstraint)/playersbought,sense=sense,rhs=constr)
    print("Fine")
    return(centreconstraint)


def run(
    #Include possibility of payback of salary
    UNCERTAINTY = True,
    #Include all players
    ALLPLAYERS = True,
    #Adjust budget
    BUDGET=132627000,
    #Four factors
    fourfactorconstr=.0,
    #Age constraint
    AGECONSTRAINT=50,
    #Max forward injuries
    MAXFINJ = 100,
    #Max Center injuries
    MAXCINJ = 100,
    #Max Guard injuries
    MAXGINJ= 100,
    #Max centers
    MAXC= 4,
    #Max guards
    MAXG=10,
    #Max forwards
MAXF=10,formula=0,turnoverst={"All":1,"Center":1,"Guard":1,"Forward":1},
    eFGt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0},
    ORBt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0},
    DRBt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0},
    FTt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0},filename="raptors.csv",MP=100,musthaves=[],alpha=0):
    
    
    try:
        free_agents=pd.read_csv("free_agents.csv")
        raptors=pd.read_csv(filename)
        raptors['free agent 2'] = raptors['free agent']
        raptors['AVG SALARY'] = raptors['salary_2020']
        raptors.rename(columns={'name': 'Player','free agent 2': 'raptors free agent'},inplace=True, errors='raise')
        raptors['Raptors']=True
        #Get rid of raptors free agents
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
        free_agents=free_agents[free_agents['MP'] >= MP].reset_index(drop=True)
        free_agents=free_agents[free_agents['AVG SALARY'] != '-'].reset_index(drop=True)


        injuries=pd.read_csv("injuries_2010-2020.csv")
        injuries=injuries[injuries['Relinquished'].isin(free_agents['Player'])]
        injuries=injuries.groupby("Relinquished").count()
        injuries=injuries[injuries.columns[0:1]]
        injuries.columns=["injuries"]
        
        free_agents=pd.merge(free_agents,injuries,left_on="Player",right_on="Relinquished",how="left")
        

        ### Turn non-percentage values to percentages --------------------------------------------------------------------------------
        percentages=free_agents.columns[free_agents.columns.str.contains("%")]
        res=[free_agents[percentage]/100 if len(free_agents[free_agents[percentage]>1])>1 else free_agents[percentage] for percentage in percentages]

        res=pd.DataFrame(res).T
        for col in list(res.columns):
            free_agents[col]=res[col]

        free_agents['eFG']= (free_agents['FG'] + 0.5 * free_agents['3P'])/ free_agents['FGA']
        free_agents['TOV_Factor']=free_agents['TOV'] / (free_agents['FGA']+ 0.44 * free_agents['FTA']+ free_agents['TOV']) 
        free_agents['FT Factor']=free_agents['FT']/free_agents['FGA']
        free_agents = free_agents.replace(np.nan, 0)
        


        typeplayer= list(set(free_agents['TYPE']))
        positions= list(set(free_agents['Pos']))

        playersall = LpVariable.dicts(name='Agent', indexs=range(len(free_agents)), cat=LpBinary) 
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

            
                 
        
        ### Objective Four Factors + WS ------------------------------------------------------------------------------------------
        eFG=lpSum(np.array(free_agents['eFG'])*np.array(list(playersall.values())))
        TOV_Factor=lpSum(np.array(free_agents['TOV_Factor'])*np.array(list(playersall.values())))
        ORB=lpSum(np.array(free_agents['ORB%'])*np.array(list(playersall.values())))
        DRB=lpSum(np.array(free_agents['DRB%'])*np.array(list(playersall.values())))
        FT=lpSum(np.array(free_agents['FT Factor'])*np.array(list(playersall.values())))



        playersbought=15

        prob = LpProblem("NBA")
        prob.sense = LpMaximize

        #divide by playersbought for gurobi instead of 15?
        objectiveWS=lpSum(free_agents['WS']*np.array(list(playersall.values())))
        objectiveFF=lpSum((.4*eFG)/playersbought - (.25*TOV_Factor)/playersbought + (.1*ORB)/playersbought + (.1*DRB)/playersbought) + lpSum((.15*FT)/playersbought)
        #probfourfactors+=objectivefourfactors
        #prob.addConstraint(LpConstraint(name="Secondary Objective",e=secondaryobjective,sense=1,rhs=fourfactorconstr))
        #-> include in Notebook

        if(formula==0):
            objective=objectiveWS
            prob+=objective
            prob.addConstraint(LpConstraint(name="Secondary Objective",e=objectiveFF,sense=1,rhs=fourfactorconstr))

        if(formula==1):
            objective=objectiveWS
            prob+=objective

        if(formula==2):
            objective=objectiveFF
            prob+=objective
        if (formula==3):
            objective=alpha*objectiveWS+(1-alpha)*100*objectiveFF
            prob+=objective


        ### Global Constraints -----------------------------------------------------------------------------------------------

        #ensure that we deduct the salary of non free agents on raptors if we choose to kick them
        for i in raptornonfreeagentsold.keys():
            inverse=LpConstraint(name="RaptorsnonAgent_sold"+str(i),e=-1+playersall[i]+raptornonfreeagentsold[i],sense=0,rhs=0) #Constraint that if we keep 1, then this variable must be the inverse 0. Ie no matter what we pay their salary
            prob.addConstraint(inverse)


        ### Must have Constraint -------------------------------------------------------------------------------------------------
        musthaves=free_agents[free_agents['Player'].isin(musthaves)]
        musthaveplayers=0
        for i in musthaves.index:
            musthaveplayers+=playersall[i]
        if(len(musthaves)>0):
            prob.addConstraint(LpConstraint(name="Must Have Players", e=lpSum(musthaveplayers),rhs=len(musthaves),sense=0))
        
        #Four Factor User input Constraints --------------------------------------------------------------------------------------
        prob.addConstraint(LpConstraint(name="Turn over Constraint",e=TOV_Factor/playersbought,rhs=turnoverst['All'],sense=-1))
        prob.addConstraint(LpConstraint(name="eFG Constraint",e=eFG/playersbought,rhs=eFGt['All'],sense=1))
        prob.addConstraint(LpConstraint(name="ORB% Constraint",e=ORB/playersbought,rhs=ORBt['All'],sense=1))
        prob.addConstraint(LpConstraint(name="DRB% Constraint",e=DRB/playersbought,rhs=DRBt['All'],sense=1))
        prob.addConstraint(LpConstraint(name="FT Constraint",e=FT/playersbought,rhs=FTt['All'],sense=1))
        
        #TOV per position
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="C",feature='TOV_Factor',cname="Center Turnover Constraint",sense=-1,constr=turnoverst['Center']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="G",feature='TOV_Factor',cname="Guard Turnover Constraint",sense=-1,constr=turnoverst['Guard']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="F",feature='TOV_Factor',cname="Forward Turnover Constraint",sense=-1,constr=turnoverst['Forward']))
        
        #eFGA per position
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="C",feature='eFG',cname="Center eFG Constraint",sense=1,constr=eFGt['Center']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="G",feature='eFG',cname="Guard eFG Constraint",sense=1,constr=eFGt['Guard']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="F",feature='eFG',cname="Forward eFG Constraint",sense=1,constr=eFGt['Forward']))
        
        #ORB% per position
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="C",feature='ORB%',cname="Center ORB Constraint",sense=1,constr=ORBt['Center']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="G",feature='ORB%',cname="Guard ORB Constraint",sense=1,constr=ORBt['Guard']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="F",feature='ORB%',cname="Forward ORB Constraint",sense=1,constr=ORBt['Forward']))
        
        #DRB% per position
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="C",feature='DRB%',cname="Center DRB Constraint",sense=1,constr=DRBt['Center']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="G",feature='DRB%',cname="Guard DRB Constraint",sense=1,constr=DRBt['Guard']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="F",feature='DRB%',cname="Forward DRB Constraint",sense=1,constr=DRBt['Forward']))
        print("We're still good")
        #FT Factor per position
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="C",feature='FT Factor',cname="Center FT Constraint",sense=1,constr=FTt['Center']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="G",feature='FT Factor',cname="Guard FT Constraint",sense=1,constr=FTt['Guard']))
        prob.addConstraint(positionalconstraintsFF(free_agents,playersall,keyword="F",feature='FT Factor',cname="Forward FT Constraint",sense=1,constr=FTt['Forward']))
        print("We're still good x2")
        #prob.addConstraint(positionalconstraintsFF(free_agents,sense=-1,cname= "Turnover Center Constraint",constr=turnoverst['Center']))
#         prob.addConstraint(positionalconstraintsFF(free_agents,keyword="G",cname="Turnover Guard Constraint",constr=turnoverst['Guard']))
#         prob.addConstraint(positionalconstraintsFF(free_agents,keyword="F",cname="Turnover Forward Constraint",constr=turnoverst['Forward']))
        
       
        
        #budget constraint:  ------------------------------------------------------------------------------------------------
        averagesalary = [int(salary) for salary in free_agents['AVG SALARY'] if salary != "-"]
        #Need to fill in NAs
        #out of the league if no average salary
        minimumsalary = 898310 #[898310,1445697,1620564,1678854,1737145,1882867,2028594,2174318,2320044,2331593,2564753]
        free_agents['AVG SALARY'] = [int(salary) if salary != "-" else minimumsalary for salary in free_agents['AVG SALARY']]
        ##notefinished
        keepcost=0 # keeping a non free agents.
        keepcostfreerapt = 0#keeping a free agent raptor
        #transactioncost=0
        
        #ensure that raptors players that aren't free agents, if kicked, we have to pay their salary
        if(UNCERTAINTY == True):
            uncertaintransactioncost= 0
            print("Uncertainty!!")
            for i in nonfree.index:
                cost=((1-nonfree['chance_of_recouping'][i])*nonfree['salary_2020'][i]*raptornonfreeagentsold[i])#+((1-nonfree['chance_of_recouping'][i])*nonfree['salary_2020'][i]*raptornonfreeagentsold[i])
                uncertaintransactioncost+=cost
                keepcost+=nonfree['salary_2020'][i]*(1-raptornonfreeagentsold[i])




            uncertaintransactioncost=lpSum(uncertaintransactioncost)
            transactioncost=uncertaintransactioncost
            print(transactioncost)
        else:
            transactioncost=0

            #transactioncost=0
            #ensure that raptors players that aren't free agents, if kicked, we have to pay their salary
            for indexrap in raptornonfreeagentsold.keys():
                transactioncost += raptornonfreeagentsold[indexrap]*free_agents['salary_2020'][indexrap]
                keepcost+=nonfree['salary_2020'][i]*(1-raptornonfreeagentsold[i])
                
        #Cost of keeping a free agent raptor
        raptorfreeagent=free_agents[(free_agents['raptors free agent']==1)]
        for indexrap in raptorfreeagent.index:
                keepcostfreerapt += playersall[indexrap]*raptorfreeagent['salary_2020'][indexrap]
        print("Transaction Cost")
        print(transactioncost)
        #free agents bought + free agents raptors kept + letting go our non free agents + keeping non free agent
        spending=lpSum(np.array(free_agents['AVG SALARY'])*np.array(list(playersall.values()))+transactioncost)#keepcostfreerapt+keepcost+transactioncost)


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
        prob.solve()
        chosen=[]
        for var in prob.variables():
            if("Agent" in var.name and "Raptor" not in var.name):
                if(var.varValue==1):
                    no=int(var.name.split("_")[1])
                    chosen.append(free_agents['Player'][no])
        RESULTS=free_agents[free_agents['Player'].isin(chosen)]
        return(prob,RESULTS)
    except Exception as e:
        print("ERROR")
        print(e)
        return("Failure",None)
















