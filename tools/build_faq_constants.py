"""Refresh FAQ constants from the source tables; do not turn estimates into standards."""
from pathlib import Path
import json,math
R=Path(__file__).resolve().parents[1];D=R/'docs'
read=lambda n:json.loads((D/n).read_text())
d=read('INVENTORY-GRID-CONTROL.json');b=d['source']['placement_bbox_pt'];w,h=d['source']['image_pixels'];aspect=((b[3]-b[1])/h)/((b[2]-b[0])/w);rows=[]
for r in d['threshold_results']:
 a=r['fits']['affine']['parameters']['matrix'];m=a[1][1]/a[1][0]*aspect;n=a[2][1]/a[2][0]*aspect
 rows.append(dict(threshold=r['threshold'],elevation_deg=math.degrees(math.asin(math.sqrt(abs(m*n)))),acute_yaw_class_deg=math.degrees(math.atan(math.sqrt(abs(m/n))))))
obj={'schema_version':1,'date':'2026-10-25','statuses':{'definition':'Mathematical or unit definition','observed':'Specific sampled source, not universal','conditional_estimate':'Model-dependent inference','tool_choice':'Implementation normalization, not a recovered publisher specification'},
 'definitions':{'pdf_points_per_inch':72,'millimeters_per_inch':25.4,'isometric_azimuth_deg':45,'isometric_elevation_deg':math.degrees(math.asin(1/math.sqrt(3)))},
 'camera':{'pilot':read('CAMERA-MEASUREMENTS.json')['measurements'],'inventory_control':{'status':'conditional_estimate','source':'INVENTORY-GRID-CONTROL.json','assumptions':'Affine approximation, horizontal square stud grid, no roll; compensate native image-to-page aspect ratio. Yaw has axis/reflection ambiguity. Perspective is not ruled out.','rows':rows,'limits':'Threshold variation is not an accuracy bound or confidence interval.'},'renderer_default':{'status':'tool_choice','azimuth_deg':35,'elevation_deg':30,'projection':'perspective','field_of_view_vertical_deg':30}},
 'normalized_layout':{'status':'tool_choice','source':'STYLE-RESEARCH.md','rounded_radius_pt':7.087,'inner_padding_pt':14.17,'page_inset_pt':12,'quantity_pt':8,'model_outline_pt':.32},
 'source_panel_samples':{'status':'observed','source':'STYLE-RESEARCH.md','creator_31051_2016':{'frame_pt':.5,'inner_radius_pt_approx':7.09,'quantity_pt':8,'step_pt':38},'modern_sampled':{'frame_pt':.75,'outer_radius_pt_approx':7.09,'inner_radius_pt_approx':6.71,'quantity_pt':8,'step_pt_typical':26},'friends_42604':{'frame_pt':2,'outer_radius_pt_approx':7.09,'inner_radius_pt_approx':6.09,'quantity_pt':8,'step_pt':26}},
 'source_scale_samples':{'status':'observed','source':'SCALE-STUDY.md','75375_p20_plate_pitch_pt':[9.13,9.09],'42221_p10_beam_hole_pitch_mm':8.0086,'42221_p16_axle3_outer_ink_mm':23.3623,'42221_page_mm':[195,259]},
 'presets':{'status':'tool_choice','source':'../brick_blueprint/presets.json','notes':'Source-linked preview colors plus normalized layout fields. Not print-ink recipes.','values':json.loads((R/'brick_blueprint/presets.json').read_text())['presets']},
 'complete_tables':{'projection':'LARGE-GRID-MEASUREMENTS.json','inventory_projection':'INVENTORY-GRID-CONTROL.json','matched_colors':'MATCHED-PART-COLORS.json','step_colors':'STEP-COLOR-CONTROLS.json','fonts':'FONT-MEASUREMENTS.json','font_downloads':'FONT-SOURCES.json','source_hashes':'STYLE-SOURCES.json','annotation_roles':'ANNOTATION-GRAMMAR.md','materials':'MATERIALS-AND-EMPHASIS.md'}}
(D/'FAQ-CONSTANTS.json').write_text(json.dumps(obj,indent=2)+'\n')
