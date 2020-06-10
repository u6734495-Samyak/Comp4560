# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import re
import os
import time
from CleanRawSheet import CleanTargets, CleanCompositions


def MatWeb_ReadHtml(alloy):
	dicts = []
	files = os.listdir("MatWeb/" + alloy)
	for fname in files:
		if fname.startswith(".") or not fname.endswith('.html'):
			continue
		f = open("MatWeb/" + alloy + '/' + fname, "r")#, encoding="utf-8")
		txt = f.read().splitlines()
		f.close()
		di = {}

		li = 0
		for line in txt:
			if "<title>" in line:
				di['Name'] = txt[li + 1][1:]
			elif "Key Words:" in line:
				kwords = txt[li + 1]
				di['Key words'] = kwords
			elif "Tensile Strength, Ultimate" in line or "Tensile Strength&nbsp;" in line:
				t = txt[li]
				di['Tensile strength'] = t[t.find('<td class="dataCell"'):t.find("MPa")]
			elif "Tensile Strength, Yield" in line:
				t = txt[li]
				di['Yield strength'] = t[t.find('<td class="dataCell"'):t.find("MPa")]
			elif "Elongation at Break" in line:
				t = txt[li]
				di['Elongation'] = t[t.find('<td class="dataCell"'):t.find("%")]
#			elif "Temperature" in line:
#				print(li, txt[li])

			elif "Component Elements Properties" in line:
				while not "</table >" in txt[li]:
					t = txt[li]
					t1 = t.find("<td style=\"vertical-align:top;\">")
					t2 = t[t1:].find("&nbsp;") + t1
					t1 += t[t1:t2].find(",") + 2
					e = t[t1:t2]
					di[e] = t[t2:t.find('%')]
					if "As " in t or "as " in t:
						di[e] = '* ' + di[e]
					
					li += 1
				break

			li += 1
			
		dicts.append(di)

	dfr = pd.DataFrame(dicts)
	
	cols = ['Name', 'Key words', 'Tensile strength', 'Yield strength', 'Elongation', alloy]
	dfr.columns = dfr.columns.astype(str).str.replace('td style="vertical-align:top;">', '', regex=False)
	dfr = pd.concat([dfr[cols], dfr.drop(cols, axis=1)], axis=1)
	return dfr.replace('<.*?>|\&nbsp;|\t', '', regex=True)


def CleanNames(df0):
	df = df0.replace('Magnesium|Aluminum|Alclad|Alloy', '', regex=True)
	dfn = df0.copy()
	dfn['Composition'] = df['Name'].replace('; .*|, .*', '', regex=True).replace('-.*', '', regex=True)
	dfn['Temper'] = (df['Name'] + ' ').replace('.*?([THOFW]\d*[^A-WYZa-wyz)][Xx]?)?', '\\1', regex=True)\
					.replace('((?:[THOFW]\d*[^A-WYZa-wyz)][Xx]?)*).*$', '\\1', regex=True)\
					.replace(',|;|\ |/+', '/', regex=True).replace('^/|/$', '', regex=True)
	dfn['Composition'] = dfn['Composition']\
					.apply(lambda x: re.sub(dfn.loc[dfn['Composition'] == x, 'Temper'].values[0], '', x))
	dfn['Condition'] = (df['Name'] + ' ').replace('.*?,(.*)', '\\1', regex=True)\
					.replace('[THOFW]\d*[^A-WYZa-wyz)][Xx]?', 'XVQ', regex=True)\
					.replace('.*XVQ', '', regex=True)\
					.replace('Alloy|\(.*\)|\(|\)', '', regex=True)
#					.replace(';+', ';', regex=True).replace('^;|;$', '', regex=True)\
	dfn['Condition'] = dfn['Condition']\
					.apply(lambda x: re.sub(dfn.loc[dfn['Condition'] == x, 'Composition'].values[0], '', x))
	dfn = dfn.replace('(^\s+|\s+$)', '', regex=True).replace(' +', ' ', regex=True).fillna('')
#	print(dfn[['Composition', 'Temper', 'Name']].to_string(index=False))
#	exit()
	return dfn


def MatWeb_HTML_to_Raw(alloy):
	dfr = MatWeb_ReadHtml(alloy)
	cols = ['Mg', 'Ag', 'Al', 'Be', 'Ca', 'Ce', 'Cu', 'Fe',
							'Gd', 'Li', 'Mn', 'Nd', 'Ni', 'Pb', 'Si', 'Sn', 'Th',
							'Tl', 'Y', 'Zn', 'Zr', 'Rare Earths', 'Other']
	dfc = dfr[cols]
	dfr = dfr.drop(cols, axis=1)
	dfr[cols] = dfc

	dfr.to_excel('MatWeb_' + alloy + '_raw.xlsx', freeze_panes=[1 , 1], index=False)


def MatWeb_Raw_to_Numerical(alloy, imp, csv, dry):
	start = time.time()
	outname = "Outputs/MatWeb_" + alloy + "_" + str(imp)
	if dry:
		return outname

	print("MatWeb_Raw_to_Numerical(), impurity = ", imp)
	dfr = pd.read_excel("MatWeb_" + alloy + "_raw.xlsx")
	dfn = CleanNames(dfr[['Name']])
	cols = ['Name', 'Key words', 'Tensile strength', 'Yield strength', 'Elongation']
	dfy = dfr[['Tensile strength', 'Yield strength', 'Elongation']]
	dfy = CleanTargets(dfy)

	dfc = CleanCompositions(dfr[['Mg', 'Ag', 'Al', 'Be', 'Ca', 'Ce', 'Cu', 'Fe',
							'Gd', 'Li', 'Mn', 'Nd', 'Ni', 'Pb', 'Si', 'Sn', 'Th',
							'Tl', 'Y', 'Zn', 'Zr', 'Rare Earths']], dfr[['Name']], imp)
#	dfc = CleanCompositions(dfr.drop(cols, axis=1), dfr[['Name']], imp)
	df_sheet = pd.concat([dfn, dfy, dfc], axis=1, sort=False)
	df_sheet.insert(1, 'Source', 'MatWeb')
	df_sheet = df_sheet[df_sheet['Name'].str.contains('Extended|extended', regex=True) == False]
	df_sheet = df_sheet.sort_values(by=['Composition', 'Tensile strength'])

	if csv:
		df_sheet.to_csv(outname + ".csv", index=False)
	else:
		df_sheet.to_excel(outname + ".xlsx", freeze_panes=[1 , 1], index=False)

	print("MatWeb_Raw_to_Numerical() took", time.time() - start, "s\n")
	return outname


if __name__ == "__main__":
	MatWeb_HTML_to_Raw("Mg")
	MatWeb_Raw_to_Numerical("Mg", 0, False, False)

