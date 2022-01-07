"""
"Signaux Faibles" project package for failure prediction computations.

The package contains several sub-packages associated with the different computations
steps:
* ``config`` - Configuration and model parameters that will be used during execution.
* ``preprocessing`` - Production of datasets from raw data. Datasets loading and
handling, exploration and feature engineering utilities.
* ``processing`` - Data processing and models execution.
* ``postprocessing`` - Scores computations, plotting and analysis tools.
"""

DATA_ROOT_DIR = (
    "/projets/TSF/sources"  # Needed by make_monthly_indics.py and make_yearly_indics.py
)
VUES_DIR = "/projets/TSF/sources/livraison_MRV-DTNUM_juin_2021"

ETL_FILES = [
    "etl_associe-ref_groupe_france",
    "etl_decla-declarations_af",
    "etl_decla-declarations_indmap",
    "etl_refent_oracle-t_jugement_histo",
    "etl_rn.d2053_pdt_ch_excep_view",
    "etl_rn.d2053_pdt_ch_exercice_ant_view",
    "etl_rn.d2056_detail_autre_prov_view",
    "etl_rn.d2056_detail_deprec_view",
    "etl_rn.d2056_detail_hausse_prix_view",
    "etl_rn.d2056_detail_immo_fi_view",
    "etl_rn.d2056_detail_impot_view",
    "etl_rn.d2056_detail_risq_charge_view",
    "etl_rn.d2058a_detail_deduc_view",
    "etl_rn.d2058a_detail_reinteg_view",
    "etl_rn.d2058b_detail_ch_a_payer_view",
    "etl_rn.d2058b_detail_prov_deprec_view",
    "etl_rn.d2058b_detail_prov_risq_view",
    "etl_rn.d2059a_detail_divers_view",
    "etl_rn.d2059a_immobilisation_pmv_view",
    "etl_rn.d2059b_detail_fusion_apport_view",
    "etl_rn.d2059f_associe_pm_view",
    "etl_rn.d2059f_associe_pp_view",
    "etl_rn.d2059g_filiale_view",
    "etl_rn.liasse_rn_view",
    "etl_rn.v_matrice_epro_rn",
    "etl_rsi.d2033b_result_deduc_view",
    "etl_rsi.d2033b_result_reint_view",
    "etl_rsi.d2033c_pv_mv_view",
    "etl_rsi.d2033d_dotation_ventil_view",
    "etl_rsi.d2033f_associe_pm_view",
    "etl_rsi.d2033f_associe_pp_view",
    "etl_rsi.d2033g_filiale_view",
    "etl_rsi.liasse_rsi_view",
    "etl_rsi.v_matrice_epro_rsi",
    "etl_tva.d3310a_eau_minerale_view",
    "etl_tva.d3310a_geothermie_view",
    "etl_tva.d3310a_hydrocarbure_view",
    "etl_tva.d3310ter_tva_secteur_view",
    "etl_tva.d3517s_eau_minerale_view",
    "etl_tva.d3517s_geothermie_view",
    "etl_tva.d3517s_hydrocarbure_view",
    "etl_tva.liasse_tva_3310a_comm_view",
    "etl_tva.liasse_tva_3310a_view",
    "etl_tva.liasse_tva_3310ter_comm_view",
    "etl_tva.liasse_tva_3310ter_view",
    "etl_tva.liasse_tva_3517ddr_comm_view",
    "etl_tva.liasse_tva_3517ddr_view",
    "etl_tva.liasse_tva_ca12_comm_view",
    "etl_tva.liasse_tva_ca12_view",
    "etl_tva.liasse_tva_ca12a_comm_view",
    "etl_tva.liasse_tva_ca12a_view",
    "etl_tva.liasse_tva_ca3_comm_view",
    "etl_tva.liasse_tva_ca3_view",
    "etl_tva.v_matrice_epro_tva",
    "pub_medoc_oracle-t_defaillance",
    "pub_refent-t_ref_entreprise",
    "pub_refent-t_ref_etablissements",
    "pub_refer-t_ref_code_nace_complet",
    "pub_refer-t_ref_lib_forme_juridique",
]

ORACLE_FILES = ["pub_risq_oracle.t_dar", "pub_risq_oracle.t_art"]
