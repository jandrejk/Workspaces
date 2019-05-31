#!/usr/bin/env python
import ROOT
import imp
import json
from array import array
wsptools = imp.load_source('wsptools', 'workspaceTools.py')


def GetFromTFile(str):
    f = ROOT.TFile(str.split(':')[0])
    obj = f.Get(str.split(':')[1]).Clone()
    f.Close()
    return obj

# Boilerplate
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.RooWorkspace.imp = getattr(ROOT.RooWorkspace, 'import')
ROOT.TH1.AddDirectory(0)
ROOT.gROOT.LoadMacro("CrystalBallEfficiency.cxx+")

w = ROOT.RooWorkspace('w')

### DESY electron/muon tag and probe results
loc = 'inputs/LeptonEfficiencies'

desyHistsToWrap = [
    (loc+'/Muon/Run2016_legacy/Muon_Run2016_legacy_IdIso.root',               'MC',   'm_idiso_desy_mc'),
    (loc+'/Muon/Run2016_legacy/Muon_Run2016_legacy_IdIso.root',               'Data', 'm_idiso_desy_data'),  
    (loc+'/Muon/Run2016_legacy/Muon_Run2016_legacy_IsoMu22.root',             'MC',   'm_trgIsoMu22_desy_mc'),
    (loc+'/Muon/Run2016_legacy/Muon_Run2016_legacy_IsoMu22.root',             'Data', 'm_trgIsoMu22_desy_data')
]

for task in desyHistsToWrap:
    wsptools.SafeWrapHist(w, ['m_pt', 'expr::m_abs_eta("TMath::Abs(@0)",m_eta[0])'],
                          wsptools.ProcessDESYLeptonSFs(task[0], task[1], task[2]), name=task[2])
for t in ['idiso_desy','trgIsoMu22_desy']:
    w.factory('expr::m_%s_ratio("@0/@1", m_%s_data, m_%s_mc)' % (t, t, t))

desyHistsToWrap = [
    (loc+'/Electron/Run2016_legacy/Electron_Run2016_legacy_IdIso.root',          'MC',   'e_idiso_desy_mc'),
    (loc+'/Electron/Run2016_legacy/Electron_Run2016_legacy_IdIso.root',          'Data', 'e_idiso_desy_data'),  
    (loc+'/Electron/Run2016_legacy/Electron_Run2016_legacy_Ele25.root',          'MC',   'e_trgEle25leg_desy_mc'),
    (loc+'/Electron/Run2016_legacy/Electron_Run2016_legacy_Ele25.root',          'Data', 'e_trgEle25leg_desy_data')
]

for task in desyHistsToWrap:
    wsptools.SafeWrapHist(w, ['e_pt', 'expr::e_abs_eta("TMath::Abs(@0)",e_eta[0])'],
                          wsptools.ProcessDESYLeptonSFs(task[0], task[1], task[2]), name=task[2])

for t in ['idiso_desy','trgEle25leg_desy']:
    w.factory('expr::e_%s_ratio("@0/@1", e_%s_data, e_%s_mc)' % (t, t, t))


### Muon tracking efficiency scale factor from the muon POG
loc = 'inputs/MuonPOG'

muon_trk_eff_hist = wsptools.TGraphAsymmErrorsToTH1D(GetFromTFile(loc+'/Tracking_EfficienciesAndSF_BCDEFGH.root:ratio_eff_eta3_dr030e030_corr'))
wsptools.SafeWrapHist(w, ['m_eta'], muon_trk_eff_hist, name='m_trk_ratio')

### Electron tracking efficiency scale factor from the egamma POG
loc = 'inputs/EGammaPOG'

electron_trk_eff_hist = GetFromTFile(loc+'/egammaEffi.txt_EGM2D.root:EGamma_SF2D')
wsptools.SafeWrapHist(w, ['e_eta','e_pt'], electron_trk_eff_hist, name='e_trk_ratio')


### KIT tau ID scale factors
loc = 'inputs/KIT/tau_id_sfs_2016.root:'
histsToWrap = [
    (loc + 'mva_m_dm0_pt30', 't_iso_mva_m_dm0_pt30_sf'),
    (loc + 'mva_m_dm1_pt30', 't_iso_mva_m_dm1_pt30_sf'),
    (loc + 'mva_m_dm10_pt30', 't_iso_mva_m_dm10_pt30_sf'),
    (loc + 'mva_t_dm0_pt40_eta2p1', 't_iso_mva_t_dm0_pt40_eta2p1_sf'),
    (loc + 'mva_t_dm1_pt40_eta2p1', 't_iso_mva_t_dm1_pt40_eta2p1_sf'),
    (loc + 'mva_t_dm10_pt40_eta2p1', 't_iso_mva_t_dm10_pt40_eta2p1_sf'),
]
for task in histsToWrap:
    wsptools.SafeWrapHist(w, ['t_pt', 'expr::t_abs_eta("TMath::Abs(@0)",t_eta[0])'],
                          GetFromTFile(task[0]), name=task[1])

wsptools.MakeBinnedCategoryFuncMap(w, 't_dm', [-0.5, 0.5, 9.5, 10.5],
                                   't_iso_mva_m_pt30_sf', ['t_iso_mva_m_dm0_pt30_sf', 't_iso_mva_m_dm1_pt30_sf', 't_iso_mva_m_dm10_pt30_sf'])

wsptools.MakeBinnedCategoryFuncMap(w, 't_dm', [-0.5, 0.5, 9.5, 10.5],
                                   't_iso_mva_t_pt40_eta2p1_sf', ['t_iso_mva_t_dm0_pt40_eta2p1_sf', 't_iso_mva_t_dm1_pt40_eta2p1_sf', 't_iso_mva_t_dm10_pt40_eta2p1_sf'])


### Hadronic tau trigger efficiencies
with open('inputs/triggerSF-Moriond17/di-tau/fitresults_tt_moriond2017.json') as jsonfile:
    pars = json.load(jsonfile)
    for tautype in ['genuine', 'fake']:
        for iso in ['VLooseIso','LooseIso','MediumIso','TightIso','VTightIso','VVTightIso']:
            for dm in ['dm0', 'dm1', 'dm10']:
                label = '%s_%s_%s' % (tautype, iso, dm)
                x = pars['data_%s' % (label)]
                w.factory('CrystalBallEfficiency::t_%s_tt_data(t_pt[0],%g,%g,%g,%g,%g)' % (
                    label, x['m_{0}'], x['sigma'], x['alpha'], x['n'], x['norm']
                ))

                x = pars['mc_%s' % (label)]
                w.factory('CrystalBallEfficiency::t_%s_tt_mc(t_pt[0],%g,%g,%g,%g,%g)' % (
                    label, x['m_{0}'], x['sigma'], x['alpha'], x['n'], x['norm']
                ))
            label = '%s_%s' % (tautype, iso)
            wsptools.MakeBinnedCategoryFuncMap(w, 't_dm', [-0.5, 0.5, 9.5, 10.5],
                                               't_%s_tt_data' % label, ['t_%s_dm0_tt_data' % label, 't_%s_dm1_tt_data' % label, 't_%s_dm10_tt_data' % label])
            wsptools.MakeBinnedCategoryFuncMap(w, 't_dm', [-0.5, 0.5, 9.5, 10.5],
                                               't_%s_tt_mc' % label, ['t_%s_dm0_tt_mc' % label, 't_%s_dm1_tt_mc' % label, 't_%s_dm10_tt_mc' % label])
            w.factory('expr::t_%s_tt_ratio("@0/@1", t_%s_tt_data, t_%s_tt_mc)' % (label, label, label))



### LO DYJetsToLL Z mass vs pT correction
wsptools.SafeWrapHist(w, ['z_gen_mass', 'z_gen_pt'],
                      GetFromTFile('inputs/zpt_weights_2016.root:zptmass_histo'), name='zptmass_weight_nom')

w.importClassCode('CrystalBallEfficiency')


w.Print()
w.writeToFile('htt_scalefactors_2016_v2.root')
w.Delete()
