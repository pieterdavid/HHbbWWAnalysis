import os
import sys
from copy import copy

from itertools import chain

import logging
logger = logging.getLogger(__name__) 

import bamboo
from bamboo.analysismodules import HistogramsModule, DataDrivenBackgroundHistogramsModule

from bamboo import treefunctions as op
from bamboo.plots import CutFlowReport, Plot, EquidistantBinning, SummedPlot

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)))) # Add scripts in this directory
from BaseHHtobbWW import BaseNanoHHtobbWW
from plotDef import *
from selectionDef import *
from JPA import *
from mvaEvaluatorSL import *
from DDHelper import DataDrivenFake, DataDrivenDY
from bamboo.root import gbl
import ROOT

'''
def switch_on_index(indexes, condition, contA, contB):
    if contA._base != contB._base:
        raise RuntimeError("The containers do not derive from the same base, this won't work")
    base = contA._base
    return [base[op.switch(condition, contA[index].idx, contB[index].idx)] for index in indexes]       
'''

#===============================================================================================#
#                                       PlotterHHtobbWW                                         #
#===============================================================================================#
class PlotterNanoHHtobbWWSL(BaseNanoHHtobbWW,DataDrivenBackgroundHistogramsModule):
    """ Plotter module: HH->bbW(->e/µ nu)W(->e/µ nu) histograms from NanoAOD """
    def __init__(self, args):
        super(PlotterNanoHHtobbWWSL, self).__init__(args)

    def initialize(self):
        super(PlotterNanoHHtobbWWSL, self).initialize()
        # Change the way the FakeExtrapolation is postProcesses (avoids overriding the `postProcess` method) 
        if "FakeExtrapolation" in self.datadrivenContributions:
            contrib = self.datadrivenContributions["FakeExtrapolation"]
            self.datadrivenContributions["FakeExtrapolation"] = DataDrivenFake(contrib.name, contrib.config)
        if "DYEstimation" in self.datadrivenContributions: 
            contrib = self.datadrivenContributions["DYEstimation"]
            self.datadrivenContributions["DYEstimation"] = DataDrivenDY(contrib.name, contrib.config,"PseudoData" in self.datadrivenContributions)

    def definePlots(self, t, noSel, sample=None, sampleCfg=None): 
        noSel = super(PlotterNanoHHtobbWWSL,self).prepareObjects(t, noSel, sample, sampleCfg, 'SL')
        # --------------------------- Machine Learning Model --------------------------- #
        # -------- for JPA --------- #
        basepath = os.path.join(os.path.abspath(os.path.dirname(__file__)),'MachineLearning','ml-models','JPA')
        resolvedModelDict = dict()
        resolvedModelDict['2b2Wj'] = [os.path.join(basepath, 'bb1l_jpa_4jet_resolved_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_4jet_resolved_odd.xml')]
        resolvedModelDict['2b1Wj'] = [os.path.join(basepath, 'bb1l_jpa_missingWJet_resolved_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_missingWJet_resolved_odd.xml')]
        resolvedModelDict['2b0Wj'] = [os.path.join(basepath, 'bb1l_jpa_missingAllWJet_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_missingAllWJet_odd.xml')]
        resolvedModelDict['1b2Wj'] = [os.path.join(basepath, 'bb1l_jpa_missingBJet_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_missingBJet_odd.xml')]
        resolvedModelDict['1b1Wj'] = [os.path.join(basepath, 'bb1l_jpa_missingBJet_missingWJet_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_missingBJet_missingWJet_odd.xml')]
        resolvedModelDict['1b0Wj'] = [os.path.join(basepath, 'bb1l_jpa_missingBJet_missingAllWJet_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_missingBJet_missingAllWJet_odd.xml')]
        resolvedModelDict['evCat'] = [os.path.join(basepath, 'bb1l_jpa_evtCat_resolved_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_evtCat_resolved_odd.xml')]
        
        boostedModelDict  = dict()
        boostedModelDict['Hbb2Wj'] = [os.path.join(basepath, 'bb1l_jpa_4jet_boosted_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_4jet_boosted_odd.xml')]
        boostedModelDict['Hbb1Wj'] = [os.path.join(basepath, 'bb1l_jpa_missingWJet_boosted_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_missingWJet_boosted_odd.xml')]
        boostedModelDict['evCat']  = [os.path.join(basepath, 'bb1l_jpa_evtCat_boosted_even.xml'), 
                                      os.path.join(basepath, 'bb1l_jpa_evtCat_boosted_odd.xml')]
        
        # ----------------------------------- NodeList ------------------------------------- #
        # keep the exact same order of nodes as mentioned in respective xml files
        ResolvedJPANodeList = ['2b2Wj','2b1Wj','1b2Wj','2b0Wj','1b1Wj','1b0Wj','0b']
        BoostedJPANodeList  = ['Hbb2Wj','Hbb1Wj']

        
        # ---------- LBN+DNN models ----------- #
        #path_model = '/home/users/f/b/fbury/bamboodev/HHbbWWAnalysis/MachineLearning/HHMachineLearning/TFModels/AllJPAVarReg_crossval/saved_model.pb'
        #path_model = "/home/users/f/b/fbury/bamboodev/HHbbWWAnalysis/MachineLearning/HHMachineLearning/TFModels/AllJPAVarReg_crossval.pb"
        path_model = '/home/ucl/cp3/gsaha/bamboodev/HHbbWWAnalysis/MachineLearning/ml-models/DNN/Resolved/ModelOneEpoch.pb'

        plots = []
        cutFlowPlots = []
        #yields = CutFlowReport("yields",printInLog=True,recursive=True)
        era = sampleCfg['era']
        
        self.sample = sample
        self.sampleCfg = sampleCfg
        self.era = era
        
        self.yieldPlots = makeYieldPlots(self.args.Synchronization)
        
        #----- Ratio reweighting variables (before lepton and jet selection) -----#
        if self.args.BtagReweightingOff or self.args.BtagReweightingOn:
            #plots.append(objectsNumberPlot(channel="NoChannel",suffix='NoSelection',sel=noSel,objCont=self.ak4Jets,objName='Ak4Jets',Nmax=15,xTitle='N(Ak4 jets)'))
            #plots.append(CutFlowReport("BtagReweightingCutFlowReport",noSel))
            return plots
            
        #----- Stitching study -----#
        if self.args.DYStitchingPlots or self.args.WJetsStitchingPlots:
            if self.args.DYStitchingPlots and sampleCfg['group'] != 'DY':
                raise RuntimeError("Stitching is only done on DY MC samples")
            if self.args.WJetsStitchingPlots and sampleCfg['group'] != 'Wjets':
                raise RuntimeError("Stitching is only done on WJets MC samples")
            #plots.extend(makeLHEPlots(noSel,t.LHE))
            #plots.append(objectsNumberPlot(channel="NoChannel",suffix='NoSelection',sel=noSel,objCont=self.ak4Jets,objName='Ak4Jets',Nmax=15,xTitle='N(Ak4 jets)'))
            #plots.append(CutFlowReport("DYStitchingCutFlowReport",noSel))
            return plots
            
            
        #----- Singleleptons -----#
        ElSelObj,MuSelObj = makeSingleLeptonSelection(self,noSel,plot_yield=True)

        # selObjectDict : keys -> level (str)
        #                 values -> [El,Mu] x Selection object
        # Select the jets selections that will be done depending on user input #
        resolved_args = ["Res2b2Wj","Res2b1Wj","Res2b0Wj","Res1b2Wj","Res1b1Wj","Res1b0Wj","Resolved"]
        boosted_args  = ["Hbb2Wj","Hbb1Wj","Boosted"]
        jet_level = resolved_args + boosted_args
        jet_level.append("Ak4")  # to call all resolved categories
        jet_level.append("Ak8")  # to call all boosted categories
        jetplot_level = [arg for (arg,boolean) in self.args.__dict__.items() if arg in jet_level and boolean]
        if len(jetplot_level) == 0:  
            jetplot_level = jet_level # If nothing said, will do all
        jetsel_level = copy(jetplot_level)  # A plot level might need a previous selection that needs to be defined but not necessarily plotted

        if any(item in boosted_args for item in jetsel_level):
            jetsel_level.append("Ak8") # SemiBoosted & Boosted needs the Ak8 selection
        if any(item in resolved_args for item in jetsel_level):
            jetsel_level.append("Ak4") # Resolved needs the Ak4 selection 

        print('jetSel_Level: {}'.format(jetsel_level))

        # Selections:    
        #---- Lepton selection ----#
        ElColl = [t.Electron[op.switch(op.rng_len(self.electronsTightSel) == 1, 
                                       self.electronsTightSel[0].idx, 
                                       self.electronsFakeSel[0].idx)]]
        MuColl = [t.Muon[op.switch(op.rng_len(self.muonsTightSel) == 1, 
                                   self.muonsTightSel[0].idx, 
                                   self.muonsFakeSel[0].idx)]]

        if not self.args.OnlyYield:
            ChannelDictList = []
            ChannelDictList.append({'channel':'El','sel':ElSelObj.sel,'suffix':ElSelObj.selName})
            ChannelDictList.append({'channel':'Mu','sel':MuSelObj.sel,'suffix':MuSelObj.selName})
                
            for channelDict in ChannelDictList:
                #----- Trigger plots -----#
                plots.extend(singleLeptonTriggerPlots(**channelDict, triggerDict=self.triggersPerPrimaryDataset))
            
        LeptonKeys   = ['channel','sel','lep','suffix','is_MC']
        JetKeys      = ['channel','sel','j1','j2','j3','j4','suffix','nJet','nbJet','is_MC']
        commonItems  = ['channel','sel','suffix']
            
        #----- Ak4 jets selection -----#
        if "Ak4" in jetsel_level:
            print("... Processing Ak4Jets Selection for Resolved category : nAk4Jets >= 3")
            ResolvedKeys = ['channel','sel','met','lep','j1','j2','j3','j4','suffix','nJet','nbJet']
            JetsN        = {'objName':'Ak4Jets','objCont':self.ak4Jets,'Nmax':10,'xTitle':'nAk4Jets'}
            FatJetsN     = {'objName':'Ak8Jets','objCont':self.ak8Jets,'Nmax':5,'xTitle':'nAk8Jets'}
            
            ElSelObjResolved = makeResolvedSelection(self,ElSelObj,copy_sel=True,plot_yield=True)
            MuSelObjResolved = makeResolvedSelection(self,MuSelObj,copy_sel=True,plot_yield=True)
        
            if self.args.onlypost:
                ElSelObjResolved.record_yields = True
                MuSelObjResolved.record_yields = True
                ElSelObjResolved.yieldTitle = 'Resolved Channel $e^{\pm}$'
                MuSelObjResolved.yieldTitle = 'Resolved Channel $\mu^{\pm}$'
                
            ChannelDictListAk4 = []
            if "Ak4" in jetplot_level and not self.args.OnlyYield:
                print ('...... Base Resolved Selection : nAk4Jets >= 3')
                ChannelDictListAk4.append({'channel':'El','sel':ElSelObjResolved.sel,'lep':ElColl[0],'met':self.corrMET,
                                           'j1':self.ak4Jets[0],'j2':self.ak4Jets[1],'j3':self.ak4Jets[2],'j4':None,
                                           'nJet':3,'nbJet':0,'suffix':ElSelObjResolved.selName,'is_MC':self.is_MC})
                ChannelDictListAk4.append({'channel':'Mu','sel':MuSelObjResolved.sel,'lep':MuColl[0],'met':self.corrMET,
                                           'j1':self.ak4Jets[0],'j2':self.ak4Jets[1],'j3':self.ak4Jets[2],'j4':None,
                                           'nJet':3,'nbJet':0,'suffix':MuSelObjResolved.selName,'is_MC':self.is_MC})

                for channelDict in ChannelDictListAk4:
                    # Singlelepton #
                    plots.extend(makeSinleptonPlots(**{k:channelDict[k] for k in LeptonKeys}))
                    # Number of jets #
                    plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**JetsN))
                    plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**FatJetsN))
                    # Ak4 Jets #
                    plots.extend(makeAk4JetsPlots(**{k:channelDict[k] for k in JetKeys},HLL=self.HLL))
                    # MET #
                    plots.extend(makeMETPlots(**{k:channelDict[k] for k in commonItems}, met=self.corrMET))
                    # High level #
                    plots.extend(makeHighLevelPlotsResolved(**{k:channelDict[k] for k in ResolvedKeys},HLL=self.HLL))

                
        ##### Ak8-b jets selection #####
        if "Ak8" in jetsel_level:
            print ("...... Processing Ak8b jet selection for SemiBoosted & Boosted Category")
            FatJetKeys  = ['channel','sel','j1','j2','j3','has1fat1slim','has1fat2slim','suffix']
            FatJetsN    = {'objName':'Ak8Jets','objCont':self.ak8Jets,'Nmax':5,'xTitle':'N(Ak8 jets)'}
            SlimJetsN   = {'objName':'Ak4Jets','objCont':self.ak4JetsCleanedFromAk8b,'Nmax':10,'xTitle':'N(Ak4 jets)'}
            BoostedKeys = ['channel','sel','met','lep','j1','j2','j3','suffix','bothAreFat','has1fat2slim']
            
            ElSelObjBoosted = makeBoostedSelection(self,ElSelObj,copy_sel=True,plot_yield=True)
            MuSelObjBoosted = makeBoostedSelection(self,MuSelObj,copy_sel=True,plot_yield=True)
            
            if self.args.onlypost:
                ElSelObjBoosted.record_yields = True
                MuSelObjBoosted.record_yields = True
                ElSelObjBoosted.yieldTitle = 'Boosted Channel $e^{\pm}$'
                MuSelObjBoosted.yieldTitle = 'Boosted Channel $\mu^{\pm}$'
                
            # Fatjets plots #
            ChannelDictListAk8 = []
            if "Ak8" in jetplot_level and not self.args.OnlyYield:
                print('boosted selection...')
                ChannelDictListAk8.append({'channel':'El','sel':ElSelObjBoosted.sel,'lep':ElColl[0],'met':self.corrMET,
                                           'j1':self.ak8BJets[0],'j2':self.ak4JetsCleanedFromAk8b[0],'j3':None,'has1fat1slim':True,'has1fat2slim':False,'bothAreFat':False,
                                           'suffix':ElSelObjBoosted.selName,'is_MC':self.is_MC})
                ChannelDictListAk8.append({'channel':'Mu','sel':MuSelObjBoosted.sel,'lep':MuColl[0],'met':self.corrMET,
                                           'j1':self.ak8BJets[0],'j2':self.ak4JetsCleanedFromAk8b[0],'j3':None,'has1fat1slim':True,'has1fat2slim':False,'bothAreFat':False,
                                           'suffix':MuSelObjBoosted.selName,'is_MC':self.is_MC})

                for channelDict in ChannelDictListAk8:
                    # Dilepton #
                    plots.extend(makeSinleptonPlots(**{k:channelDict[k] for k in LeptonKeys}))
                    # Number of jets #
                    plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**FatJetsN))
                    plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**SlimJetsN))
                    # Ak8 Jets #
                    plots.extend(makeSingleLeptonAk8JetsPlots(**{k:channelDict[k] for k in FatJetKeys},nMedBJets=self.nMediumBTaggedSubJets, HLL=self.HLL))
                    # MET #
                    plots.extend(makeMETPlots(**{k:channelDict[k] for k in commonItems}, met=self.corrMET))
                    # HighLevel #
                    plots.extend(makeHighLevelPlotsBoosted(**{k:channelDict[k] for k in BoostedKeys}, HLL=self.HLL))

        
        leptonCont = {'El':ElColl[0],'Mu':MuColl[0]}
        #self.nodes = ['DY','GGF','H','Rare','ST','TT','VBF','WJets']
        self.nodes = ['GGF','H','Rare','ST','TT','VBF','WJets']
        inputsEventNr    = returnEventNr(self, t)
        # ========================== JPA Resolved Categories ========================= #
        if any(item in resolved_args for item in jetsel_level):
            def cleanVBFwithJPA_Resolved(jpaJets, nJpaJets):
                return lambda j : op.OR(*(op.deltaR(jpaJets[i].p4, j.p4) > 0.8 for i in range(nJpaJets)))
            ChannelDictList = []
            selObjectDNNDictList = []
            # dict = {'key':'Node', 'value' : [refined selObj, [JPAjetIndices]]}
            elL1OutList, elL2OutList, ElResolvedSelObjJetsIdxPerJpaNodeDict = findJPACategoryResolved (self, ElSelObjResolved, ElColl[0],self.muonsPreSel, self.electronsPreSel, 
                                                                                                       self.ak4Jets, self.ak4BJetsLoose,self.ak4BJets, self.corrMET, 
                                                                                                       resolvedModelDict, t.event,self.HLL, ResolvedJPANodeList, 
                                                                                                       plot_yield=True)
            muL1OutList, muL2OutList, MuResolvedSelObjJetsIdxPerJpaNodeDict = findJPACategoryResolved (self, MuSelObjResolved, MuColl[0],self.muonsPreSel, self.electronsPreSel, 
                                                                                                       self.ak4Jets, self.ak4BJetsLoose,self.ak4BJets, self.corrMET, 
                                                                                                       resolvedModelDict, t.event,self.HLL, ResolvedJPANodeList,
                                                                                                       plot_yield=True)
            
            if "Res2b2Wj" in jetplot_level or "Resolved" in jetplot_level:
                print ('...... JPA : 2b2Wj Node Selection')
                ElSelObjResolved2b2Wj        = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('2b2Wj')[0]
                ElSelObjResolved2b2WjJets    = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('2b2Wj')[1]
                MuSelObjResolved2b2Wj        = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('2b2Wj')[0]
                MuSelObjResolved2b2WjJets    = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('2b2Wj')[1]
                print('...... ', ElSelObjResolved2b2Wj.selName)
                ElSelObjResolved2b2WjVBFJets = op.sort(op.combine(op.select(self.VBFJets, cleanVBFwithJPA_Resolved(ElSelObjResolved2b2WjJets, 4)), N=2, pred=self.lambda_VBFPair),
                                                       lambda dijet : -op.invariant_mass(dijet[0].p4,dijet[1].p4))
                MuSelObjResolved2b2WjVBFJets = op.sort(op.combine(op.select(self.VBFJets, cleanVBFwithJPA_Resolved(MuSelObjResolved2b2WjJets, 4)), N=2, pred=self.lambda_VBFPair),
                                                       lambda dijet : -op.invariant_mass(dijet[0].p4,dijet[1].p4))
                print(type(ElSelObjResolved2b2WjVBFJets[0]))

                if self.args.onlypost:
                    ElSelObjResolved2b2Wj.record_yields = True
                    MuSelObjResolved2b2Wj.record_yields = True
                    ElSelObjResolved2b2Wj.yieldTitle = 'Resolved2b2Wj Channel $e^{\pm}$'
                    MuSelObjResolved2b2Wj.yieldTitle = 'Resolved2b2Wj Channel $\mu^{\pm}$'
                

                inputsClassic_2b2Wj_El = returnClassicInputs_2b2Wj(self, ElColl[0], ElSelObjResolved2b2WjJets[0], ElSelObjResolved2b2WjJets[1], 
                                                                   ElSelObjResolved2b2WjJets[2], ElSelObjResolved2b2WjJets[3], ElSelObjResolved2b2WjVBFJets)
                inputsLBN_2b2Wj_El     = returnLBNInputs_2b2Wj(self, ElColl[0], ElSelObjResolved2b2WjJets[0], ElSelObjResolved2b2WjJets[1], 
                                                               ElSelObjResolved2b2WjJets[2], ElSelObjResolved2b2WjJets[3])

                inputsClassic_2b2Wj_Mu = returnClassicInputs_2b2Wj(self, MuColl[0], MuSelObjResolved2b2WjJets[0], MuSelObjResolved2b2WjJets[1], 
                                                                   MuSelObjResolved2b2WjJets[2], MuSelObjResolved2b2WjJets[3], MuSelObjResolved2b2WjVBFJets)
                inputsLBN_2b2Wj_Mu     = returnLBNInputs_2b2Wj(self, MuColl[0], MuSelObjResolved2b2WjJets[0], MuSelObjResolved2b2WjJets[1], 
                                                               MuSelObjResolved2b2WjJets[2], MuSelObjResolved2b2WjJets[3])

                input_names_2b2Wj = [key[0] for key in inputsClassic_2b2Wj_El.keys()] + ['LBN_inputs','eventnr']
                output_name = "Identity"

                DNN = op.mvaEvaluator(path_model,mvaType='Tensorflow',otherArgs=(input_names_2b2Wj, output_name))

                inputs_array_2b2Wj_El = [op.array("double",val) for val in inputStaticCast(inputsClassic_2b2Wj_El,"float")]
                inputs_array_2b2Wj_El.append(op.array("double",*inputStaticCast(inputsLBN_2b2Wj_El,"float")))
                inputs_array_2b2Wj_El.append(op.array("long",*inputStaticCast(inputsEventNr,"long")))
                inputs_array_2b2Wj_Mu = [op.array("double",val) for val in inputStaticCast(inputsClassic_2b2Wj_Mu,"float")]
                inputs_array_2b2Wj_Mu.append(op.array("double",*inputStaticCast(inputsLBN_2b2Wj_Mu,"float")))
                inputs_array_2b2Wj_Mu.append(op.array("long",*inputStaticCast(inputsEventNr,"long")))
                
                DNNScore_2b2Wj_El = DNN(*inputs_array_2b2Wj_El)
                DNNScore_2b2Wj_Mu = DNN(*inputs_array_2b2Wj_Mu)

                selObjectDNNDictList.append({'channel':'El','selObject':ElSelObjResolved2b2Wj,'DNN_Inputs':inputs_array_2b2Wj_El,'DNN_Score':DNNScore_2b2Wj_El})
                selObjectDNNDictList.append({'channel':'Mu','selObject':MuSelObjResolved2b2Wj,'DNN_Inputs':inputs_array_2b2Wj_Mu,'DNN_Score':DNNScore_2b2Wj_Mu})

                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjResolved2b2Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':ElSelObjResolved2b2WjJets[0],'j2':ElSelObjResolved2b2WjJets[1],
                                            'j3':ElSelObjResolved2b2WjJets[2],'j4':ElSelObjResolved2b2WjJets[3],
                                            'nJet':4,'nbJet':2,'suffix':ElSelObjResolved2b2Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjResolved2b2Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':MuSelObjResolved2b2WjJets[0],'j2':MuSelObjResolved2b2WjJets[1],
                                            'j3':MuSelObjResolved2b2WjJets[2],'j4':MuSelObjResolved2b2WjJets[3],
                                            'nJet':4,'nbJet':2,'suffix':MuSelObjResolved2b2Wj.selName,
                                            'is_MC':self.is_MC})
                    
            if "Res2b1Wj" in jetplot_level or "Resolved" in jetplot_level:
                print ('...... JPA : 2b1Wj Node Selection')
                ElSelObjResolved2b1Wj        = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('2b1Wj')[0]
                ElSelObjResolved2b1WjJets    = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('2b1Wj')[1]
                MuSelObjResolved2b1Wj        = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('2b1Wj')[0]
                MuSelObjResolved2b1WjJets    = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('2b1Wj')[1]
                print('...... ', ElSelObjResolved2b1Wj.selName)

                if self.args.onlypost:
                    ElSelObjResolved2b1Wj.record_yields = True
                    MuSelObjResolved2b1Wj.record_yields = True
                    ElSelObjResolved2b1Wj.yieldTitle = 'Resolved2b1Wj Channel $e^{\pm}$'
                    MuSelObjResolved2b1Wj.yieldTitle = 'Resolved2b1Wj Channel $\mu^{\pm}$'
                
                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjResolved2b1Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':ElSelObjResolved2b1WjJets[0],'j2':ElSelObjResolved2b1WjJets[1],
                                            'j3':ElSelObjResolved2b1WjJets[2],'j4':None,
                                            'nJet':3,'nbJet':2,'suffix':ElSelObjResolved2b1Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjResolved2b1Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':MuSelObjResolved2b1WjJets[0],'j2':MuSelObjResolved2b1WjJets[1],
                                            'j3':MuSelObjResolved2b1WjJets[2],'j4':None,
                                            'nJet':3,'nbJet':2,'suffix':MuSelObjResolved2b1Wj.selName,
                                            'is_MC':self.is_MC})
                    
            if "Res2b0Wj" in jetplot_level or "Resolved" in jetplot_level:
                print ('...... JPA : 2b0Wj Node Selection')
                ElSelObjResolved2b0Wj          = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('2b0Wj')[0]
                ElSelObjResolved2b0WjJets      = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('2b0Wj')[1]
                MuSelObjResolved2b0Wj          = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('2b0Wj')[0]
                MuSelObjResolved2b0WjJets      = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('2b0Wj')[1]
                print('...... ', ElSelObjResolved2b0Wj.selName)

                if self.args.onlypost:
                    ElSelObjResolved2b0Wj.record_yields = True
                    MuSelObjResolved2b0Wj.record_yields = True
                    ElSelObjResolved2b0Wj.yieldTitle = 'Resolved2b0Wj Channel $e^{\pm}$'
                    MuSelObjResolved2b0Wj.yieldTitle = 'Resolved2b0Wj Channel $\mu^{\pm}$'                

                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjResolved2b0Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':ElSelObjResolved2b0WjJets[0],'j2':ElSelObjResolved2b0WjJets[1],
                                            'j3':None,'j4':None,
                                            'nJet':2,'nbJet':2,'suffix':ElSelObjResolved2b0Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjResolved2b0Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':MuSelObjResolved2b0WjJets[0],'j2':MuSelObjResolved2b0WjJets[1],
                                            'j3':None,'j4':None,
                                            'nJet':2,'nbJet':2,'suffix':MuSelObjResolved2b0Wj.selName,
                                            'is_MC':self.is_MC})
                    
            if "Res1b2Wj" in jetplot_level or "Resolved" in jetplot_level:
                print ('...... JPA : 1b2Wj Node Selection')
                ElSelObjResolved1b2Wj        = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('1b2Wj')[0]
                ElSelObjResolved1b2WjJets    = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('1b2Wj')[1]
                MuSelObjResolved1b2Wj        = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('1b2Wj')[0]
                MuSelObjResolved1b2WjJets    = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('1b2Wj')[1]
                print('...... ', ElSelObjResolved1b2Wj.selName)
                
                if self.args.onlypost:
                    ElSelObjResolved1b2Wj.record_yields = True
                    MuSelObjResolved1b2Wj.record_yields = True
                    ElSelObjResolved1b2Wj.yieldTitle = 'Resolved1b2Wj Channel $e^{\pm}$'
                    MuSelObjResolved1b2Wj.yieldTitle = 'Resolved1b2Wj Channel $\mu^{\pm}$'

                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjResolved1b2Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':ElSelObjResolved1b2WjJets[0],'j2':ElSelObjResolved1b2WjJets[1],
                                            'j3':ElSelObjResolved1b2WjJets[2],'j4':None,
                                            'nJet':3,'nbJet':1,'suffix':ElSelObjResolved1b2Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjResolved1b2Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':MuSelObjResolved1b2WjJets[0],'j2':MuSelObjResolved1b2WjJets[1],
                                            'j3':MuSelObjResolved1b2WjJets[2],'j4':None,
                                            'nJet':3,'nbJet':1,'suffix':MuSelObjResolved1b2Wj.selName,
                                            'is_MC':self.is_MC})
                    
            if "Res1b1Wj" in jetplot_level or "Resolved" in jetplot_level:
                print ('...... JPA : 1b1Wj Node Selection')
                ElSelObjResolved1b1Wj        = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('1b1Wj')[0]
                ElSelObjResolved1b1WjJets    = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('1b1Wj')[1]
                MuSelObjResolved1b1Wj        = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('1b1Wj')[0]
                MuSelObjResolved1b1WjJets    = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('1b1Wj')[1]
                print('...... ', ElSelObjResolved1b1Wj.selName)
            
                if self.args.onlypost:
                    ElSelObjResolved1b1Wj.record_yields = True
                    MuSelObjResolved1b1Wj.record_yields = True
                    ElSelObjResolved1b1Wj.yieldTitle = 'Resolved1b1Wj Channel $e^{\pm}$'
                    MuSelObjResolved1b1Wj.yieldTitle = 'Resolved1b1Wj Channel $\mu^{\pm}$'

                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjResolved1b1Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':ElSelObjResolved1b1WjJets[0],'j2':ElSelObjResolved1b1WjJets[1],
                                            'j3':None,'j4':None,
                                            'nJet':2,'nbJet':1,'suffix':ElSelObjResolved1b1Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjResolved1b1Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':MuSelObjResolved1b1WjJets[0],'j2':MuSelObjResolved1b1WjJets[1],
                                            'j3':None,'j4':None,
                                            'nJet':2,'nbJet':1,'suffix':MuSelObjResolved1b1Wj.selName,
                                            'is_MC':self.is_MC})
                    
            if "Res1b0Wj" in jetplot_level or "Resolved" in jetplot_level:
                print ('...... JPA : 1b0Wj Node Selection')
                ElSelObjResolved1b0Wj        = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('1b0Wj')[0]
                ElSelObjResolved1b0WjJets    = ElResolvedSelObjJetsIdxPerJpaNodeDict.get('1b0Wj')[1]
                MuSelObjResolved1b0Wj        = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('1b0Wj')[0]
                MuSelObjResolved1b0WjJets    = MuResolvedSelObjJetsIdxPerJpaNodeDict.get('1b0Wj')[1]
                print('...... ', ElSelObjResolved1b0Wj.selName)

                if self.args.onlypost:
                    ElSelObjResolved1b0Wj.record_yields = True
                    MuSelObjResolved1b0Wj.record_yields = True
                    ElSelObjResolved1b0Wj.yieldTitle = 'Resolved1b0Wj Channel $e^{\pm}$'
                    MuSelObjResolved1b0Wj.yieldTitle = 'Resolved1b0Wj Channel $\mu^{\pm}$'
                
                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjResolved1b0Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':ElSelObjResolved1b0WjJets[0],'j2':None,
                                            'j3':None,'j4':None,
                                            'nJet':1,'nbJet':1,'suffix':ElSelObjResolved1b0Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjResolved1b0Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':MuSelObjResolved1b0WjJets[0],'j2':None,
                                            'j3':None,'j4':None,
                                            'nJet':1,'nbJet':1,'suffix':MuSelObjResolved1b0Wj.selName,
                                            'is_MC':self.is_MC})
            '''        
            for channelDict in ChannelDictList:
                # Singlelepton #
                plots.extend(makeSinleptonPlots(**{k:channelDict[k] for k in LeptonKeys}))
                # Number of jets #
                plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**JetsN))
                plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**FatJetsN))
                # Ak4 Jets #
                plots.extend(makeAk4JetsPlots(**{k:channelDict[k] for k in JetKeys},HLL=self.HLL))
                # MET #
                plots.extend(makeMETPlots(**{k:channelDict[k] for k in commonItems}, met=self.corrMET))
                # High level #
                plots.extend(makeHighLevelPlotsResolved(**{k:channelDict[k] for k in ResolvedKeys},HLL=self.HLL))
            ''' 
                
        
            # ML
            for selObjectDNNDict in selObjectDNNDictList:
                lepton = leptonCont[selObjectDNNDict['channel']]
                inputs = selObjectDNNDict['DNN_Inputs']
                output = selObjectDNNDict['DNN_Score']
                selObjNodesDict = makeDNNOutputNodesSelections(self,selObjectDNNDict['selObject'],output,suffix='_v1')
                #plots.extend(makeDoubleLeptonMachineLearningInputPlots(selObjectDNNDict['selObject'].sel,selObjectDNNDict['selObject'].selName,selObjectDNNDict['channel'],inputs))
                plots.extend(makeDoubleLeptonMachineLearningOutputPlots(selObjNodesDict,output,self.nodes,channel=selObjectDNNDict['channel']))
                
        # ========================== JPA Boosted Categories ========================= #
        if any(item in boosted_args for item in jetsel_level):
            def cleanVBFwithJPA_Boosted(jpaJets, nJpaJets):
                return lambda j : op.AND(op.rng_len(self.ak8BJets) >= 1, op.OR(op.OR(*(op.deltaR(jpaJets[i].p4, j.p4) > 0.8 for i in range(nJpaJets))),
                                                                               op.deltaR(self.ak8Jets[0].p4, j.p4) > 1.2))
            ChannelDictList = []
            # dict = {'key':'Node', 'value' : [refined selObj, [JPAjetIndices]]}    
            foo,bar,ElBoostedSelObjJetsIdxPerJpaNodeDict = findJPACategoryBoosted (self, ElSelObjBoosted, ElColl[0], self.muonsPreSel, self.electronsPreSel, 
                                                                                   self.ak8BJets, self.ak4JetsCleanedFromAk8b, self.ak4BJetsLoose, 
                                                                                   self.ak4BJets, self.corrMET, boostedModelDict, t.event, self.HLL, BoostedJPANodeList,
                                                                                   plot_yield=True)
            foo,bar,MuBoostedSelObjJetsIdxPerJpaNodeDict = findJPACategoryBoosted (self, MuSelObjBoosted, MuColl[0], self.muonsPreSel, self.electronsPreSel, 
                                                                                   self.ak8BJets, self.ak4JetsCleanedFromAk8b, self.ak4BJetsLoose, 
                                                                                   self.ak4BJets, self.corrMET, boostedModelDict, t.event, self.HLL, BoostedJPANodeList, 
                                                                                   plot_yield=True)

            if "Hbb2Wj" in jetplot_level or "Boosted" in jetplot_level:
                print ('...... JPA : Hbb2Wj Node Selection')
                ElSelObjBoostedHbb2Wj        = ElBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb2Wj')[0]
                ElSelObjBoostedHbb2WjJets    = ElBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb2Wj')[1]
                MuSelObjBoostedHbb2Wj        = MuBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb2Wj')[0]
                MuSelObjBoostedHbb2WjJets    = MuBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb2Wj')[1]
                
                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjBoostedHbb2Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':self.ak8BJets[0],'j2':ElSelObjBoostedHbb2WjJets[0],'j3':ElSelObjBoostedHbb2WjJets[1],
                                            'has1fat1slim':False,'has1fat2slim':True,'bothAreFat':False,
                                            'suffix':ElSelObjBoostedHbb2Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjBoostedHbb2Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':self.ak8BJets[0],'j2':MuSelObjBoostedHbb2WjJets[0],'j3':MuSelObjBoostedHbb2WjJets[1],
                                            'has1fat1slim':False,'has1fat2slim':True,'bothAreFat':False,
                                            'suffix':MuSelObjBoostedHbb2Wj.selName,
                                            'is_MC':self.is_MC})
                    
            if "Hbb1Wj" in jetplot_level or "Boosted" in jetplot_level:
                print ('...... JPA : Hbb1Wj Node Selection')
                ElSelObjBoostedHbb1Wj        = ElBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb1Wj')[0]
                ElSelObjBoostedHbb1WjJets    = ElBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb1Wj')[1]
                MuSelObjBoostedHbb1Wj        = MuBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb1Wj')[0]
                MuSelObjBoostedHbb1WjJets    = MuBoostedSelObjJetsIdxPerJpaNodeDict.get('Hbb1Wj')[1]
                
                if not self.args.OnlyYield:
                    ChannelDictList.append({'channel':'El','sel':ElSelObjBoostedHbb1Wj.sel,'lep':ElColl[0],'met':self.corrMET,
                                            'j1':self.ak8BJets[0],'j2':ElSelObjBoostedHbb1WjJets[0],'j3':None,
                                            'has1fat1slim':True,'has1fat2slim':False,'bothAreFat':False,
                                            'suffix':ElSelObjBoostedHbb1Wj.selName,
                                            'is_MC':self.is_MC})
                    ChannelDictList.append({'channel':'Mu','sel':MuSelObjBoostedHbb1Wj.sel,'lep':MuColl[0],'met':self.corrMET,
                                            'j1':self.ak8BJets[0],'j2':MuSelObjBoostedHbb1WjJets[0],'j3':None,
                                            'has1fat1slim':True,'has1fat2slim':False,'bothAreFat':False,
                                            'suffix':MuSelObjBoostedHbb1Wj.selName,
                                            'is_MC':self.is_MC})
                        

            for channelDict in ChannelDictList:
                # Dilepton #
                plots.extend(makeSinleptonPlots(**{k:channelDict[k] for k in LeptonKeys}))
                # Number of jets #
                plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**FatJetsN))
                plots.append(objectsNumberPlot(**{k:channelDict[k] for k in commonItems},**SlimJetsN))
                # Ak8 Jets #
                plots.extend(makeSingleLeptonAk8JetsPlots(**{k:channelDict[k] for k in FatJetKeys},nMedBJets=self.nMediumBTaggedSubJets, HLL=self.HLL))
                # MET #
                plots.extend(makeMETPlots(**{k:channelDict[k] for k in commonItems}, met=self.corrMET))
                # HighLevel #
                plots.extend(makeHighLevelPlotsBoosted(**{k:channelDict[k] for k in BoostedKeys}, HLL=self.HLL))
                
                      
                
        #----- Add the Yield plots -----#
        plots.append(self.yields)
        #plots.extend(cutFlowPlots)
        return plots

