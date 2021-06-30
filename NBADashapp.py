import dash
import dash_core_components as dcc 
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
from dash.exceptions import PreventUpdate
import json
from helper import *
import pandas as pd

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets = external_stylesheets,
                meta_tags=[{"name": "viewport", "content": "width=device-width"}])


global RESULTS
RESULTS= pd.DataFrame()

fffields=["Turnover Maximum","eFG Minimum","ORB Minimum","DRB Minimum","FT Minimum"]
positions=["All","Center","Guard","Forward"]
ffpositional = [pos+" "+field for field in fffields for pos in positions]
# App layout
ALLOWED_TYPES = (
    "text", "text", "number", "number", "number",
    "number", "number", "number","number","number",
    "number","number",
    "number", "number","number","number",
    "number", "number","number","number",
    "number", "number","number","number",
    "number", "number","number","number",
    "number", "number","number","number","text","number","text","number",
)
FIELD_NAMES = [
    "Uncertainty (y/n)","All Players (y/n)", "Budget","Four Factors (0-1)","Average Age",
    "Max Forward Injuries","Max Center Injuries","Max Guard Injuries","Max Centers","Max Guards","Max Forwards","WS+FF,WS,FF (0,1,2)"]+ffpositional+["Initial Roster Filename"]+['MP Minimum','Must have Player','alpha']


app.layout = html.Div([

    html.H1("NBA App", style={'text-align': 'center'}),
    html.Center(html.Iframe(src="https://public.tableau.com/views/NBA_16146218806790/TeamComparison?:showVizHome=no&:embed=true"
           ,style={"height": "700px", "width": "100%"})),
    html.Div(
#         [
#             dcc.Input(
#             id="input_{}".format(_),
#             type=_,
#             placeholder="input type {}".format(_),
#             )
#             for _ in range(len(ALLOWED_TYPES))
            
#         ]
#         + [html.Div(id="out-all-types")],
        [
            dcc.Input(
                id="input_{}".format(idn),
                type=_,
                placeholder=fieldname,
                debounce=True,
            )
            for _,fieldname,idn in zip(ALLOWED_TYPES,FIELD_NAMES,range(len(ALLOWED_TYPES)))
        ]+ [html.Div(id="out-all-types")]
    ),    
    html.Br(),

    html.Div([
          html.Center(dcc.Markdown("""
              **Results**
          """,)),#style={'marginLeft': 500}),
          html.Center(html.Pre(id='results')),

      ],className='row',style={'backgroundColor': 'rgb(240,248,255)'}
    ),

])

@app.callback(
    Output("results", "children"),
    [Input("input_{}".format(_), "value") for _ in range(len(ALLOWED_TYPES))],
)
def cb_render(*vals):
    allfilled=True
    for val in vals:
        if(val==None):
            allfilled=False
            print(allfilled)
        else:
            print(True)
    if(allfilled==True):
        #Include possibility of payback of salary
        if("y" in vals[0]):
            UNCERTAINTY = True
            print("Uncertainty!")
        else:
            UNCERTAINTY = False
        #Include all players
        if("y" in vals[1]):
            ALLPLAYERS = True
        else:
            ALLPLAYERS = False
        #Adjust budget
        BUDGET= vals[2]
        #Four factors
        fourfactorconstr= vals[3]
        #Age constraint
        AGECONSTRAINT= vals[4]
        #Max forward injuries
        MAXFINJ = vals[5]
        #Max Center injuries
        MAXCINJ = vals[6]
        #Max Guard injuries
        MAXGINJ= vals[7]
        #Max centers
        MAXC= vals[8]
        #Max guards
        MAXG= vals[9]
        #Max forwards
        MAXF= vals[10]
        formula=vals[11]
        turnoverst=dict(zip(positions,vals[12:16]))
        eFGt=dict(zip(positions,vals[16:20]))
        ORBt=dict(zip(positions,vals[20:24]))
        DRBt=dict(zip(positions,vals[24:28]))
        FTt=dict(zip(positions,vals[28:32]))
        
        filename=vals[32]
        MPmin=vals[33]
        musthaves=vals[34].split(",")
        alpha=vals[35]
        print("FTt:")
        print(FTt)
    
        prob,datares=run(UNCERTAINTY, ALLPLAYERS,BUDGET,fourfactorconstr,
                         AGECONSTRAINT,MAXFINJ,MAXCINJ,MAXGINJ,MAXC,MAXG,
                         MAXF,formula,turnoverst=turnoverst,eFGt=eFGt,ORBt=ORBt,DRBt=DRBt,FTt=FTt,
                         filename=filename,MP=MPmin,alpha=alpha)
        if(prob=="Failure"):
            return("FAILURE")
        print(value(prob.objective))
        res=showresults(prob)

    else:
        #Include possibility of payback of salary
        if(vals[0]):
            if("y" in vals[0]):
                UNCERTAINTY = True
                print("UNCERTAINty!")
            else:
                UNCERTAINTY = False
        else:
            UNCERTAINTY = False
            print("UNCERTAINty!")
        #Include all players
        if(vals[1]):
            if("y" in vals[1]):
                ALLPLAYERS = True
            else:
                ALLPLAYERS = False
        else:
            ALLPLAYERS = False
        #Adjust budget
        if(vals[2]):
            BUDGET= vals[2]
        else:  
            BUDGET=132627000
        #Four factors
        if(vals[3]):
            fourfactorconstr=vals[3]
        else:
            fourfactorconstr=.0
        #Age constraint
        if(vals[4]):
            AGECONSTRAINT=vals[4]
        else:
            AGECONSTRAINT=50
        #Max forward injuries
        if(vals[5]):
            MAXFINJ = vals[5]
        else:
            MAXFINJ = 100
        #Max Center injuries
        if(vals[6]):
            MAXCINJ=vals[6]
        else:
            MAXCINJ = 100
        #Max Guard injuries
        if(vals[7]):
            MAXGINJ=vals[7]
        else:
            MAXGINJ=100
        #Max centers
        if(vals[8]):
            MAXC = vals[8]
        else:
            MAXC= 4
        #Max guards
        if(vals[9]):
            MAXG = vals[9]
        else:
            MAXG=10
        #Max forwards
        if(vals[10]):
            MAXF=vals[10]
        else:
            MAXF = 10
        if(vals[11]):
            formula=vals[11]
        else:
            formula=0
            
        if(vals[12:16].count(None) !=4):
            toadd = [value if value != None else 1 for value in vals[12:16]]
            turnoverst=dict(zip(positions,toadd))
        else:
            turnoverst={"All":1,"Center":1,"Guard":1,"Forward":1}
        if(vals[16:20].count(None) !=4):
            toadd = [value if value != None else 0 for value in vals[16:20]]
            eFGt=dict(zip(positions,toadd))
        else:
            eFGt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0}
            
        if(vals[20:24].count(None)!=4):
            toadd = [value if value != None else 0 for value in vals[20:24]]
            ORBt=dict(zip(positions,toadd))
        else:
            ORBt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0}
            
        if(vals[24:28].count(None)!=4):
            toadd  = [value if value != None else 0 for value in vals[24:28]]
            DRBt=dict(zip(positions,toadd ))
        else:
            DRBt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0}
            
        if(vals[28:32].count(None)!=4):
            toadd  = [value if value != None else 0 for value in vals[28:32]]
            FTt=dict(zip(positions,toadd ))
        else:
            FTt={"All":.0,"Center":.0,"Guard":.0,"Forward":.0}
        if(vals[32]):
            filename=vals[32]
        else:
            filename="raptors.csv"
        if(vals[33]):
            MPmin=vals[33]
        else:
            MPmin=100
        if(vals[34]):
            musthaves=vals[34].split(",")
        else:
            musthaves=[]
        if(vals[35]):
            alpha=vals[35]
        else:
            alpha=0
        prob,datares=run(UNCERTAINTY, ALLPLAYERS,BUDGET,fourfactorconstr,
                         AGECONSTRAINT,MAXFINJ,MAXCINJ,MAXGINJ,MAXC,MAXG,
                         MAXF,formula,turnoverst=turnoverst,eFGt=eFGt,ORBt=ORBt,DRBt=DRBt,FTt=FTt,
                         filename=filename,MP=MPmin,musthaves=musthaves,alpha=alpha)
        if(prob=="Failure"):
            return("FAILURE")
        print(value(prob.objective))
        res=showresults(prob)
    former=pd.DataFrame()
    diff=""
    try:
        former=pd.read_csv("datares.csv")
        print("Good")
    except:
        pass
    reducedcost,shadow = sensitivity(prob)
    datares=datares['Player,AVG SALARY,Pos,Age,Tm,G,MP,free agent,raptors free agent,salary_2020,Raptors,injuries,eFG,TOV_Factor,ORB%,DRB%,WS,FT Factor'.split(",")]
    datares.to_csv("datares.csv")

    if(len(former)):
        print("Getting differences!")
        diff=str(set(former['Player'])-set(datares['Player']))
        print("Differences")
        print(diff)
    if(prob.status==1):
        status="success"
    else:
        status="failure"
    moneyspent = str(sum(datares['AVG SALARY']))
    averageFF = {ff:sum(datares[ff])/len(datares) for ff in ['eFG','TOV_Factor','ORB%','DRB%','WS','FT Factor']}
    return(status+"\n\nMoney Spent: "+moneyspent+"\n\nSpecs: "+str(averageFF)+"\n\nRoster:\n\n"+datares.to_string()+"\n\nDifference from last:\n\n"+diff+"\n\nSummary\n\n"+res+"\n\nReducedCosts\n\n"+reducedcost.to_string()+"\n\nShadow Price and Slack\n\n"+shadow.to_string())
    
# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True, host = '127.0.0.1')