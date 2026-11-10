# Manuscript wording for the 47-marker annotation study

This text supplies the retained manuscript sections and captions. Figures and numerical sources use the same frozen partitions and accepted predictions. The Google Doc is edited separately in Suggesting mode.

## Revised paragraphs

<!-- Source paragraph 12 -->

Methods: We benchmarked these components using a healthy human intestine CO-Detection by indEXing (CODEX) dataset comprising 220,082 cells across eight tissue regions from donor B004. Expert reference labels included 10,495 Noise cells, representing cells without a confident cell-type assignment. Four frozen clustering partitions were annotated by four large language models using 47-marker means alone or the same means plus fractions of processed values above zero. The primary annotation endpoint equally weighted two test regions.

<!-- Source paragraph 14 -->

Results: Spillover-compensation effects varied across six segmentation methods, tissue regions and cell types, with no consistent improvement across metrics. We compared Leiden, FlowSOM, SpatialSort and PIXIE against reference annotations and evaluated GPT-6 Astra, Claude Opus 5.5, Gemini 4 Argon and DeepSeek V4.1 Flash 1017 for cluster annotation. All 9,024 requested cluster predictions were delivered. With means plus fractions, reference agreement across the 16 method–model combinations ranged from 23.06% to 58.12% in the equally weighted test regions. Adding fractions increased agreement in 9 of 16 comparisons and reduced agreement in 7.

<!-- Source paragraph 16 -->

Conclusion: These results show that scalable CODEX annotation is constrained by image processing, cluster composition, marker representation and model interpretation. Automated workflows can reduce manual annotation burden, but supporting-marker review and expert validation remain necessary, particularly for rare cell types and mixed clusters.

<!-- Source paragraph 36 -->

Agentic and human-in-the-loop systems extend direct LLM annotation by adding validation, refinement, or expert feedback. CASSIA combines annotation with iterative validation and quality assessment, with optional retrieval and refinement agents [29]. The CellMaster preprint describes both automated annotation and human-in-the-loop refinement [30]. We focus on direct annotation of fixed CODEX clusters from numerical marker-expression profiles.

<!-- Source paragraph 38 -->

We address these gaps by evaluating spillover compensation across recent cell segmentation foundation models, comparing four distinct clustering methods, and testing GPT, Gemini, Claude and DeepSeek for annotation of the resulting CODEX clusters. We compare annotation from all 47 marker means with annotation from identical means plus fractions of processed marker values above zero, using the original 28-label vocabulary and the same test regions.

<!-- Source paragraph 50 -->

Changes in which cells remained after processing were assessed separately from changes among shared segmentation objects, using the matching criteria and exclusion records described in Section 2.4. These processing exclusions were distinct from the reference annotation Noise. For the before–after comparison of shared segmentation objects, regional cell-type pairs were retained when reference or predicted cells of that type were present in either condition. F1 was set to zero when neither reference nor predicted cells of that type were present in a condition. Pairs absent in both conditions were excluded.

<!-- Source paragraph 70 -->

We performed a retrospective benchmark of clustering and LLM annotation using a previously published HuBMAP CODEX dataset of healthy human large and small intestine [3]. All 220,082 cells from eight B004 tissue regions were linked to reference annotations by exact, unique (File_ID, ID) keys. The annotation evidence comprised 47 protein markers. All models could predict the original 28 dataset labels, including Noise, Paneth, NK and M1 and M2 macrophages as distinct outputs. Cell-level reference agreement is the fraction of cells whose predicted label matches the provided reference label; it does not independently establish biological correctness.

<!-- Source paragraph 72 -->

The clustering inputs differed by method and are summarized in Table S2. Leiden, FlowSOM and SpatialSort used all 47 protein markers. PIXIE used its image-derived cell-composition representation. Annotation evidence used the same 47 markers for all four partitions. Regional results describe variation within donor B004, which was the only donor in this clustering and annotation study. No new specimens were collected.

<!-- Source paragraph 74 -->

Reference labels came from the processed dataset. The annotation analysis retained the original 28-label vocabulary without merging classes. The 20-class mapping used only for the clustering diagnostics in Figure 2 is specified in Section 2.9 and Supplementary Methods, Section SM2.

<!-- Source paragraph 80 -->

Raw CODEX images were processed with the published intestine workflow [3]. The eight reference image records identify Cytokit segmentation followed by SPRM, with Hoechst1 nuclei and Cytokeratin cell channels. The six-method compensation analysis used separate segmentation outputs from those used in the main clustering benchmark. For each retained cell, x-y centroid coordinates were available in the processed H5AD, together with mean intensity for each marker within the cell mask.

<!-- Source paragraph 94 -->

We used fixed, method-specific clustering configurations for Leiden, FlowSOM, SpatialSort and PIXIE. We evaluated the fixed partitions using weighted cluster purity, the maximum agreement attainable when each unchanged cluster receives one allowed label. SpatialSort sampling seed 43 supplied a clustering sensitivity analysis and was not an additional annotation input.

<!-- Source paragraph 102 -->

For cell-type F1 and recall, each fixed cluster received its most frequent harmonized reference label across all eight B004 regions. Both heatmaps used 209,587 non-Noise cells and 20 harmonized classes, including Paneth to Goblet. This differs from the annotation analysis, which retains all 28 original labels including Noise. F1 and recall were calculated from those assignments. Full scoring definitions are in Supplementary Methods, Section SM4.

<!-- Source paragraph 108 -->

Each cluster profile contained all 47 marker means. Authoritative processed expression values were transformed as arcsinh(x/5), then cluster means were standardized using marker centers and population standard deviations fitted on the 90,296 cells in the four training regions. A scale of one was used only for an exactly constant marker. Fractions were calculated as the proportion of processed values strictly above zero before transformation or standardization. Both arrays were encoded as integer thousandths. These numerical fractions were not validated measures of biological marker positivity.

<!-- Source paragraph 110 -->

A physical model call denotes one execution of an LLM. A logical request item denotes one prescribed group of anonymous cluster queries, and an annotation set combines the request items for one method, model and input arm.

<!-- Source paragraph 112 -->

2.11 Paired marker representations

<!-- Source paragraph 114 -->

The means-only arm contained all 47 standardized marker means. The means-plus-fractions arm reused exactly the same means and added the corresponding 47 numerical fractions. Memberships, opaque query IDs, marker and cluster order, vocabulary and batch boundaries were fixed within pairs. Prompts requested exactly one integer label code per anonymous query ID and a JSON-object response. They contained no reference labels or profiles, clustering-method names, neighborhood summaries, retrieval, tools or web access.

<!-- Source paragraph 118 -->

GPT-6 Astra, Claude Opus 5.5, Gemini 4 Argon and DeepSeek V4.1 Flash 1017 each annotated the four frozen clustering outputs with both marker representations, giving 32 logical annotation sets. The 1,128 occupied clusters required four request items per method, at most 75 clusters per item, giving 128 initial items and 9,024 requested cluster predictions. All requests used supported high-reasoning settings. Model identities, actual output ceilings, seeds where supported, transport, attempts, usage and charges are preserved with the request and response records. Each logical condition contributed one accepted prediction set; recovery attempts are recorded separately (Supplementary Note 2).

<!-- Source paragraph 124 -->

Cell-level reference agreement was calculated as the number of cells whose model-assigned label matched their original reference label, divided by N, the number of cells in the stated evaluation population:

<!-- Source paragraph 126 -->

The primary analysis calculated agreement separately in each of the two test regions and averaged the two values equally. These regions contained 69,576 cells in total. Fixed-28-label macro-F1 was calculated within each region, with absent-class F1 set to zero, and then averaged equally. Noise remained a valid label; any non-Noise prediction on a reference-Noise cell counted as an error. Missing or invalid predictions remained errors in the full planned denominator. Cell- and cluster-level delivery coverage were reported separately. Full-cohort displays retained all 220,082 cells, including 10,495 reference-Noise cells.

<!-- Source paragraph 130 -->

The ratio divides direct cell-level matches by matches attainable under cluster-majority labeling in the same evaluation population and label vocabulary. Minority-reference cells counted as matches whenever the model predicted their label. Secondary reference-Noise-excluded scoring removed cells only at evaluation, while predicted Noise on retained cells remained an error. Supplementary Methods, Section SM4 provides further calculation details. The aggregate error identity is

<!-- Source paragraph 136 -->

For displays summarizing predictions across the four LLMs, we used one accepted prediction per model and each cluster’s most frequent label, resolving ties in Astra, Opus, Argon and DeepSeek order without using reference labels. This display summary does not measure repeated-call consistency.

<!-- Source paragraph 138 -->

2.14 End-to-end Leiden–Opus analysis

<!-- Source paragraph 140 -->

The Leiden–Claude Opus 5.5 pairing was prespecified for the end-to-end illustration before annotation outcomes were inspected. Its three example clusters were the largest occupied Leiden clusters by cell count, with cluster-ID tie-breaking. The pipeline was not selected by reference agreement. Spatial displays used the fixed Figure 2C region.

<!-- Source paragraph 142 -->

2.15 Study partitions and annotation evaluation

<!-- Source paragraph 144 -->

B004 regions were assigned to four training, two validation and two test regions containing 90,296, 60,210 and 69,576 cells, respectively. The training cells determined marker normalization. Reference labels were excluded from annotation prompts, query construction and model-selected display groups. Cluster memberships and profiles used full B004 data, including training and evaluation cells, so the study evaluates annotation of existing partitions in previously examined data rather than prospective generalization.

<!-- Source paragraph 146 -->

The means-plus-fractions arm supplied the primary four-model benchmark. The paired comparison used means-plus-fractions minus means for the same method, model, cluster and test region. We reported each test-region value, their equal-weighted mean, paired label changes and delivery coverage. Primary scoring retained all 28 labels including Noise. No repeated-call mean, standard deviation, vote fraction or calibrated confidence was estimated.

<!-- Source paragraph 156 -->

2.16 Response validation and execution records

<!-- Source paragraph 158 -->

Each request item was accepted atomically only after validating a complete terminal response with every expected query ID exactly once, no extra or duplicate keys or fields, integer label codes in the fixed 28-label vocabulary, and no refusal or truncation. Invalid attempts and interrupted streams remained in the execution archive. Explicitly authorized recoveries supplied missing logical items; no accepted prior output was overwritten. Each physical generation and charge was recorded once, and unresolved billing holds remained separate from confirmed charges. This recovery process does not provide independent repetitions.

<!-- Source paragraph 164 -->

We reported absolute metrics, regional changes and within-donor variation. Agreement and paired F1 differences were expressed in percentage points. B004 regions were subsamples of one donor and were not biological replicates. Annotation macro-F1 used the fixed 28-label vocabulary, with absent-class F1 set to zero. One accepted prediction per condition does not establish repeated-call stability or calibrated uncertainty.

<!-- Source paragraph 166 -->

Supplementary Table S7 reports the 12 clustering-diagnostic comparisons, with Holm correction across the complete family. Exact paired sign-flip tests weighted the eight B004 regions equally. Regional bootstrap intervals described sampled-region variation. Full calculations and observations are in Supplementary Methods, Section SM5. Annotation and paired-representation outcomes are descriptive single-run results.

<!-- Source paragraph 168 -->

These conditional clustering calculations assume joint exchangeability under independent regional sign reversals: under the null hypothesis, reversing the direction of any subset of regional differences would leave their joint distribution unchanged. The sampling design does not establish this assumption, and shared fitted partitions and reference-majority labels can couple regions. The calculations do not establish superiority across donors or remove retrospective selection bias. All 12 clustering comparisons and their paired regional observations are provided with no missing pairs.

<!-- Source paragraph 172 -->

We linked analyses to exact cell IDs, marker order, the original label vocabulary, frozen partitions, prompts and accepted predictions, and reconstructed predictions from stored raw responses before scoring. Source and membership checksums, request hashes, per-attempt receipts, strict parsing, coverage and confirmed charges are preserved with the reproducible scoring and figure sources. Supplementary Notes 1–2 and Supplementary Methods document inputs, execution and calculations.

<!-- Source paragraph 198 -->

To compare workflows at a common requested cluster count, we targeted 300 clusters using fixed method-specific configurations. Leiden and PIXIE each produced 300 occupied clusters, FlowSOM produced 299, and the primary SpatialSort run produced 229 (Table S2A).

<!-- Source paragraph 206 -->

Using the original 28 labels including Noise, pooled cluster-majority upper bounds were 68.69% for Leiden, 47.14% for FlowSOM, 48.35% for SpatialSort and 52.94% for PIXIE (Figure S5). All 220,082 B004 cells were retained, including eight cells without measurable marker signal in a separate PIXIE group. SpatialSort sampling seeds 42 and 43 produced 229 and 231 occupied clusters, respectively, with a pooled partition ARI of 0.458. Completion of both 100-sweep chains does not establish convergence.

<!-- Source paragraph 212 -->

We assigned each cluster’s predicted label to its constituent cells and compared the assignments with the original 28 reference labels. The primary benchmark used the means-plus-fractions arm and equally weighted the two test regions. Reference-majority upper bounds describe the constraints of the fixed partitions, while macro-F1 retains all 28 labels (Figures 3B–C and S7).

<!-- Source paragraph 214 -->

Across the 16 clustering-method–model combinations, mean test-region reference agreement ranged from 23.06% to 58.12%, and fixed-28-label macro-F1 ranged from 0.151 to 0.449 (Figures 3B–C). Leiden–GPT-6 Astra had the highest agreement in these two test regions. These comparisons describe one accepted annotation per condition in B004 and do not establish general model or method superiority.

<!-- Source paragraph 218 -->

All 128 logical request items returned accepted outputs, covering all 9,024 planned cluster predictions. Cluster- and cell-level delivery coverage was 100% in every final annotation set. Failed and interrupted physical attempts remained in the execution record rather than being treated as independent repeats (Supplementary Note 2).

<!-- Source paragraph 220 -->

Reference agreement varied across models and reference cell types in the Leiden test-region comparison (Figure 3D). Cell-type results used the same original label definitions as the primary benchmark.

<!-- Source paragraph 222 -->

Spatial maps compare reference labels with the four models’ Leiden predictions in the fixed Figure 2C region (Figure 3E). These maps retain individual predictions and were not selected by their annotation agreement.

<!-- Source paragraph 224 -->

The primary benchmark and paired marker-representation comparison used the same frozen partitions, original 28-label vocabulary and accepted predictions. The paired comparison is reported in Section 3.5, Tables S6a–S6d and Figure S10.

<!-- Source paragraph 226 -->

3.4 End-to-end evaluation of the Leiden–Opus annotation pipeline

<!-- Source paragraph 228 -->

We characterized the prespecified Leiden–Opus 5.5 pipeline using confusion matrices, cell-type F1 and fixed-cluster reference-majority bounds (Figure 4). The pairing and example-cluster selection were fixed before annotation outcomes were inspected.

<!-- Source paragraph 230 -->

The pooled test-region confusion matrix and cell-type F1 scores show how reference agreement varied across cell types and the two test regions (Figures 4B–C and S6A). Pooled test-region summaries weight cells equally and therefore differ from the equal-region primary endpoint.

<!-- Source paragraph 232 -->

Figures 4D–E and S6B compare full-cohort reference agreement with the maximum agreement achievable by assigning one label to each fixed cluster. The displayed components are reference agreement, the gap to maximum agreement and the within-cluster minority-label fraction. Reference agreement includes minority-reference cells whose label matches the assigned model label. These arithmetic components do not identify mutually exclusive groups of misclassified cells or causally attribute errors to pipeline stages. Figure 4E weights clusters by cell count; Figure S7 separately reports the primary equal-test-region decomposition.

<!-- Source paragraph 234 -->

The three largest Leiden clusters are shown in Figure 4D with their model-assigned and reference-majority labels. Their selection depended only on cluster size, with cluster-ID tie-breaking, rather than agreement or marker appearance.

<!-- Source paragraph 236 -->

Across all 220,082 cells, Leiden–Opus 5.5 achieved 48.27% reference agreement against a fixed-cluster upper bound of 68.69%, leaving a 20.41-percentage-point gap (Figure 4E). These full-cohort components are descriptive and are not the held-out test-region endpoint.

<!-- Source paragraph 238 -->

3.5 Paired marker-representation comparison

<!-- Source paragraph 240 -->

We compared means alone with the identical means plus fractions of processed marker values above zero across all four clustering methods and four models. Both arms delivered every planned prediction. Adding fractions increased agreement in 9 of 16 comparisons and reduced agreement in 7, with equal-test-region changes ranging from -8.75 to +6.50 percentage points (Tables S6a–S6c; Figure S10).

<!-- Source paragraph 242 -->

The comparison describes the observed single-run outcomes under the two input representations. It does not establish repeated-call stability, and fractions above zero are numerical summaries of processed measurements rather than validated biological positivity. Figure S11 compares stored marker-expression profiles of model-consensus CD8+ T groups, reflecting the combined clustering and annotation assignments without reference-label filtering.

<!-- Source paragraph 266 -->

Cell-level annotation agreement reflects both the composition of the fixed clusters and the model-assigned label. Differences in marker-expression profiles of model-consensus CD8+ T groups therefore do not independently validate those assignments (Figure S11). We recommend reporting cell-type and regional results alongside overall agreement and reviewing images and markers where predictions disagree.

<!-- Source paragraph 268 -->

The paired marker-expression results show how annotation changed when the same 47-marker means were supplemented with fractions of processed values above zero under the tested high-reasoning, 28-label conditions. The comparison is descriptive, and the fractions were not validated measures of biological positivity.

<!-- Source paragraph 270 -->

Our study evaluated direct numerical-profile annotation. We did not test the iterative validation and retrieval described in CASSIA [29] or the human-in-the-loop refinement described in the CellMaster preprint [30]. Whether these steps improve CODEX annotation remains an open question. Numerical comparisons with published RNA-sequencing results require accounting for differences in modality, tissue, label definitions and evaluation metrics.

<!-- Source paragraph 272 -->

The largest-cluster illustrations show that cluster composition and model label choice both constrain reference agreement (Figure 4D). Future systems could support expert review by displaying supporting and conflicting markers and allowing “unknown” or “mixed” labels. Noise remained a dataset reference label rather than an abstention output in this study.

<!-- Source paragraph 276 -->

This study has several limitations. The clustering and annotation benchmark included eight tissue regions from one donor, and full-cohort cluster memberships and profiles included the evaluation cells. The two test regions therefore assess labeling of existing partitions in previously examined B004 data, not prospective donor generalization. Generalization to new donors, diseases, tissues or marker panels requires further evaluation. Reference labels may contain errors or uncertain boundaries, and the cluster-majority upper bound depends on the reference-label composition of the evaluated clusters.

<!-- Source paragraph 278 -->

The available records do not establish whether reference labels informed selection of the original clustering configurations. Method-specific preprocessing and different occupied cluster counts limit attribution of differences to the clustering algorithms alone.

<!-- Source paragraph 280 -->

Additional limitations include the lack of independently verified cell boundaries and incomplete records of preprocessing steps. One accepted annotation per condition does not estimate repeated-call variability or calibrated confidence, and recovery attempts do not supply independent repetitions. No independent second set of cell-type annotations was obtained.

<!-- Source paragraph 284 -->

The conditional clustering tests in Supplementary Table S7 assume regional sign exchangeability and do not resolve dependence from shared clusters or retrospective selection. With eight regional pairs, exact tests have limited resolution after Holm correction. This does not establish equivalence or rule out important differences. Annotation agreement, cell-type results and paired marker-representation changes remain descriptive single-run observations within B004.

<!-- Source paragraph 288 -->

To develop scalable CODEX annotation workflows, image processing, clustering, marker representation and label assignment should be evaluated together. Compensation benefits varied with the workflow, and cluster composition limited reference agreement when each cluster received one label. The four-model annotation benchmark and paired marker-representation comparison showed condition-specific agreement within B004. Expert review of markers, spatial context and mixed clusters remains necessary; performance in new donors and repeated-call stability require separate evaluation.

<!-- Source paragraph 408 -->

Figure 3. Annotation benchmark using 47-marker cluster profiles. (A) Workflow from frozen clustering assignments and anonymous marker evidence to model predictions and reference-label evaluation. (B) Reference agreement and (C) fixed-28-label macro-F1 for the means-plus-fractions arm, averaged equally across the two test regions. The original 28-label vocabulary includes Noise; absent-class F1 is zero. (D) Cell-type reference agreement (recall) for Leiden predictions, using pooled test cells in the fixed ontology order. (E) Reference labels and the four models' Leiden predictions in the fixed mid-jejunum region shown in Figure 2C, using the same cell-type colors. Each model supplies one accepted prediction per cluster and arm. There are no repeated-annotation error bars. All regions are from donor B004.

<!-- Source paragraph 411 -->

Figure 4. Prespecified Leiden–Opus 5.5 annotation pipeline using means plus fractions. (A) Workflow from CODEX cell features through Leiden clustering and Opus annotation to spatial visualization. The workflow illustration was created with BioRender.com. (B) Row-normalized confusion matrix for pooled test cells. (C) Cell-type F1 for pooled test cells (bars) and each of the two test regions (points). All 28 labels, including Noise, remain in the scoring vocabulary. (D) Reference-agreement decomposition for the three largest Leiden clusters, selected by total cell count with cluster-ID tie-breaking before examining annotation outcomes. (E) The same decomposition across all 220,082 B004 cells. D and E show agreement, the gap between agreement and the cluster-majority upper bound, and the within-cluster minority-reference-label fraction. These are arithmetic components of reference disagreement, not independent biological error classes. The illustrative pipeline was selected before the annotation outcomes.

<!-- Source paragraph 415 -->

Figure S1. Cluster-quality metrics before and after spillover compensation across segmentation methods. (A) Silhouette scores by imaged tissue region, (B) Davies–Bouldin indices, and (C) Calinski–Harabasz indices calculated in PCA space for data segmented using Mesmer, CellposeCyto3, CellposeSAM, CellSAM, InstanSeg, or MicroSAM. Gray and blue bars show the mean across tissue regions before and after REDSEA compensation, respectively. Each point represents one imaged tissue region (n = 8), and lines connect paired measurements from the same imaged tissue region. Higher silhouette scores and Calinski–Harabasz indices indicate improved cluster separation, whereas lower Davies–Bouldin indices indicate improved cluster separation. These descriptive metrics were calculated from the stored PCA representations. The before–after comparison of shared segmentation objects and sensitivity to matching rules and clustering workflow are reported separately in Figure S3. Source data: Duke Research Data Repository record 565 (see Availability of Data and Materials).

<!-- Source paragraph 427 -->

Figure S4. Reference cell types and comparative clustering evaluation. (A) Stored marker means and fractions above 0.0 across 27 original non-Noise reference types (209,587 cells), using all 47 stored protein markers (45 H5AD X channels plus CD123 and CDX2 observation columns) without another transformation. Dot size shows above-cutoff fractions, which are not validated marker-positive fractions. Color shows mean expression min–max scaled to 0–1 independently by marker across the displayed types. (B) Reference-label maps across eight regions. (C) Reference-type composition of the 50 largest clusters per method (60 for FlowSOM), ordered by decreasing cell count, with colored segments indicating reference types. (D) Regional adjusted Rand index (ARI) and adjusted mutual information (AMI) (black dots, n = 8), cluster-level reference-label Shannon diversity and purity, and cell-type F1 and recall after majority labeling. Panel D uses 27 original non-Noise reference labels, distinct from the 20-class mapping in Figure 2. Lower Shannon diversity indicates less heterogeneous clusters. Colored points denote cluster-majority reference labels for diversity and purity, and reference types for F1 and recall. Boxes show interquartile ranges, center lines medians and whiskers 1.5 times the interquartile range.

<!-- Source paragraph 430 -->

Figure S5. Reference agreement upper bounds for the primary clustering assignments. (A) Cluster-majority upper bounds using the original 28 reference labels including Noise. Bars use pooled regions and points use labels assigned within each of the eight regions. All 220,082 B004 cells are retained, including eight cells without measurable marker signal in a separate PIXIE group. All regions are from donor B004.

<!-- Source paragraph 432 -->

Figure S6. Leiden–Opus 5.5 annotation diagnostics for the means-plus-fractions arm. (A) Confusion matrices for pooled test cells, shown as cell counts and row fractions over the fixed 28-label vocabulary including Noise. Rows without reference cells have zero row fractions. (B) Reference-agreement decomposition for all 300 Leiden clusters across all 220,082 B004 cells. Clusters are ordered by decreasing cluster-majority reference fraction, with cluster-ID tie-breaking, and displayed in four consecutive blocks of 75. Selected cluster IDs label each block. Green denotes agreement, orange the gap to the cluster-majority upper bound, and gray the within-cluster minority-reference-label fraction.

<!-- Source paragraph 436 -->

Counts are pooled across eight B004 regions. Processed counts refer to objects in the processed H5ADs after preprocessing. Matched counts include all objects accepted by directed nearest-neighbor matching at a maximum distance of 10 source-coordinate units after interchanging the reference x and y coordinates. Multiple segmented objects could match the same reference cell. Shared segmentation objects had the same CellID within a region and unchanged coordinates. Before-only and after-only counts use CellID, not saved row indices. The before–after comparison of shared segmentation objects further required an accepted match to the same reference cell and label in both conditions, so the shared-ID column is not its final scoring denominator. These counts describe retention and correspondence, not segmentation-boundary accuracy.

<!-- Source paragraph 444 -->

Membership refers to inputs used for clustering, not all channels available in the source images. Hoechst1 is a DNA channel. PIXIE uses selected-channel pixel intensities to construct vectors of pixel-metacluster fractions. Table_S1_channel_membership.csv lists all 48 channel names, source locations, OME aliases, method membership and supporting evidence.

<!-- Source paragraph 460 -->

Original segmentation targets (whole cells or nuclei), channels, software versions, checkpoints, inference thresholds, mask quality-control rules, runtime and hardware could not be verified for the six compensation workflows. The Cytokit+SPRM attribution and Hoechst1/Cytokeratin channels in Section 2.6 apply only to the reference dataset. Current defaults and comparable whole-cell settings were not assumed.

<!-- Source paragraph 464 -->

The annotation analysis retains the original 28 reference labels, including Noise, without class merges. The 20-class clustering diagnostics in Figure 2 exclude Noise and combine selected naming variants and classes, including Paneth to Goblet (Section 2.9). These mappings are separate analysis definitions and are not interchangeable. Full per-label mappings are preserved with the clustering scoring policy and the annotation ontology.

<!-- Source paragraph 470 -->

Supplementary Table S7 includes all six method pairs for each of weighted F1 and cluster purity, with Holm correction across the 12-test family. Two-sided exact sign-flip tests enumerated all 256 sign assignments for eight equally weighted regional differences. Reported quantities were regional means, differences in percentage points, raw and adjusted p-values, and descriptive 95% intervals from 10,000 paired-region resamples with seed 42. All 12 planned comparisons retained every regional pair. The unestablished exchangeability assumption, regional dependence and limits on donor-level inference are stated in Section 2.17.

<!-- Source paragraph 471 -->

Supplementary Note 1. LLM prompt templates and model outputs for cell-type annotation.

<!-- Source paragraph 473 -->

The four models received numerical profiles for all 47 markers, anonymous cluster query identifiers, the original 28-label code dictionary including Noise, and fixed task instructions. The means-plus-fractions arm added a fraction matrix to the identical means matrix. Neither arm received reference labels or profiles, clustering-method identities, neighborhood summaries, retrieval, tools or web access. Requests specified exactly one allowed integer label code for every query ID in a JSON object. Literal requests, prompt hashes, anonymous-to-cluster mappings and accepted raw outputs are preserved with the reproducible analysis.

<!-- Source paragraph 475 -->

Supplementary Note 2. LLM inputs, execution and response handling.

<!-- Source paragraph 476 -->

Inputs and design. All 220,082 B004 cells contributed to the frozen cluster profiles. The four partitions contained 300 Leiden, 299 FlowSOM, 229 SpatialSort and 300 PIXIE clusters. The design contained four models, two input arms and one accepted annotation per condition: 32 annotation sets, 128 initial request items and 9,024 cluster predictions. Each request item contained at most 75 clusters. Training-only normalization, integer-thousandth encoding, deterministic paired-arm order and exact join and leakage checks were frozen before launch.

<!-- Source paragraph 477 -->

Execution and acceptance. GPT-6 Astra and Claude Opus 5.5 used Batch transport; Gemini 4 Argon and DeepSeek V4.1 Flash 1017 also have separately recorded recovery attempts. All scientific requests used high reasoning. Actual model bindings, routes, token ceilings, supported seeds, transport and attempt status are recorded per physical generation rather than inferred from a model alias. Final outputs were accepted only after strict, complete JSON validation and saved-response replay. Missing outputs were recovered only after explicit authorization; prior accepted outputs and every failed or interrupted attempt were preserved.

Costs and delivery. All 128 logical items were accepted, covering all 9,024 requested cluster predictions. Confirmed campaign charges totaled US$77.08. Unresolved billing holds were retained separately and were not treated as observed charges. Recovery generations were counted as physical attempts, not independent repetitions or additional scientific conditions. The final accepted prediction bank maps each logical request to its accepted output and all supporting provenance.

<!-- Source paragraph 486 -->

Scoring and reporting. The primary endpoint is the equal-weighted mean of reference agreement across the same two test regions. Fixed-28-label macro-F1 treats absent classes as zero. Means-plus-fractions minus means changes reuse the accepted outputs, with paired label changes and full-denominator coverage reported separately. There is one accepted annotation per condition and no across-repetition standard deviation, within-model voting or calibration analysis. Figures 3–4, S6–S7, S10–S11 and Tables S6a–S6d use these same primary partitions and accepted predictions.

<!-- Source paragraph 490 -->

Figure S7. Reference-agreement decomposition for the 16 clustering-method/model combinations in the means-plus-fractions arm. For each test region, the fraction of correctly labeled cells, the gap to the cluster-majority upper bound, and the within-cluster minority-reference-label fraction sum to one. The two test-region fractions are averaged equally. The original 28-label vocabulary includes Noise. Values inside bars are percentages. The components describe arithmetic reference disagreement and do not identify independent biological error mechanisms. Each condition uses one accepted annotation per cluster.

<!-- Source paragraph 513 -->

Values are single-run outcomes after equally averaging the same two test regions. Paired changes are means-plus-fractions minus means in percentage points (pp). Missing or invalid predictions remain errors in the full planned denominator.

<!-- Source paragraph 515 -->

Macro-F1 uses all 28 labels, with absent-class F1 set to zero in each test region. Prediction coverage is the proportion of cells with a valid prediction. Values equally average the two test-region outcomes and have no across-repetition standard deviation.

<!-- Source paragraph 517 -->

Both terms use the full region denominator and sum to the means-plus-fractions minus means agreement change. The label term counts net reference matches gained or lost when both arms returned valid labels. The delivery term counts matches gained or lost when only one arm returned a valid label. Neither term estimates labels for failed calls. All final predictions were delivered, so delivery terms are zero and observed agreement changes arise from label changes. Changes are percentage points (pp).

<!-- Source paragraph 519 -->

All requests used OpenRouter with supported high reasoning, no tools or retrieval, at most 75 clusters per item and no automatic model/provider fallback. The table records actual model identities, transport, supported seeds, output ceilings, per-attempt status, usage and confirmed charges. Requests and recovery attempts are linked to prompt, parser and source hashes. Requested output ceilings differ from observed token use; recovery attempts do not provide independent repetitions.

<!-- Source paragraph 521 -->

Figure S10. Descriptive comparison of all-marker means with means plus fractions for (A) GPT-6 Astra, (B) Claude Opus 5.5, (C) Gemini 4 Argon and (D) DeepSeek V4.1 Flash 1017. Points show reference agreement averaged equally across the two test regions, using the fixed 28-label vocabulary including Noise. Lines connect the two input arms for the same frozen clustering method. Each arm uses one accepted annotation per cluster; no across-repetition SD or repeatability estimate is shown. Means, marker order, anonymous query IDs, label vocabulary and request batch boundaries are identical within each input pair; only the fractions matrix is added.

<!-- Source paragraph 542 -->

Complete numerical sources, accepted prediction mappings, execution receipts and reproducible scoring and figure scripts are provided with the GitHub revision. Tables S1–S2 and S7 document compensation and clustering; Tables S6a–S6d report the paired annotation outcomes, delivery and execution settings. Companion benchmark tables provide regional, cell-type, cluster and confusion-matrix values. Existing versioned releases and original source evidence remain preserved separately from the active analysis.

<!-- Source paragraph 591 -->

Table S7: Clustering-only conditional_comparisons.csv and paired_regional_observations.csv; all 12 planned clustering comparisons and their paired regional observations.

<!-- Source paragraph 599 -->

Figure S11. Marker profiles of cells assigned CD8+ T by each clustering method. (A) A single accepted prediction from each of the four models contributes to a most-frequent-label summary for each cluster; ties follow the fixed Astra, Opus, Argon and DeepSeek order. Row counts indicate cells in clusters assigned CD8+ T by that summary. All 47 stored marker channels are displayed, including CD123 and CDX2. Dot color shows mean stored processed expression, min–max scaled independently by marker across the four displayed method groups; no additional transformation is applied. Dot size shows the fraction of processed values strictly above zero, which is a numerical cutoff rather than validated biological marker positivity. This cross-model display does not measure repeated-call consistency.

## Active figure scope

Figures 1–4, S1–S7, S10 and S11 are retained. The independent compensation analyses remain distinct from the 47-marker clustering and annotation study. The one-annotation benchmark and paired-input study contain 32 logical sets, 128 initial request items and 9,024 accepted cluster predictions.
