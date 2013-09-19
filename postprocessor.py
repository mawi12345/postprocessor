#!/usr/bin/env python3

import argparse
import re
import logging
import io
import os

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='transform Pro/CLfile files to G-Codes', epilog='''\

Samples:

  -> transform a single file:
  postprocessor -o programm.din programm.ncl.1
   
  -> tranform all files in directory "cncfiles"
  postprocessor cncfiles
  
  -> transform a single file to stout:
  postprocessor programm.ncl.1

''')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="count")
                    
parser.add_argument("-r", "--recursive", help="recursive search for Pro/CLfiles",
                    action="store_true")
                    
parser.add_argument("-f", "--force", help="overwrite genartated G-Code files",
                    action="store_true")
                    
parser.add_argument("-c", "--no-comments", help="do not include comments",
                    action="store_true", dest='no_comments')
                    
parser.add_argument('--file-extension', dest='file_extension',
                   metavar='extension', default='din',
                   help='step the file extension (default: din)')
                   
parser.add_argument('--num-steps', dest='num_steps', type=int,
                   metavar='N', default=1,
                   help='step size for line numbers (default: 1)')
                   
parser.add_argument('--num-start', dest='num_start', type=int,
                   metavar='N', default=1,
                   help='start line numbers (default: 1)')
                   
parser.add_argument('-o', '--output', dest='output',
                   metavar='FILE', help='DIN G-Codes file')
                   
parser.add_argument("file", metavar='file', help="Pro/CLfile  Version 2.0")

clfile_pattern = re.compile('(.*)\.ncl\.(\d+)')
goto_pattern = re.compile('GOTO / (-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?)')
rapid_pattern = re.compile('RAPID')
loadtl_pattern = re.compile('LOADTL / (\d+)')
fedrat_pattern = re.compile('FEDRAT / (\d+(\.\d+)?),\s+(IPM|MMPM)')
circle_pattern = re.compile('CIRCLE / (-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?),\s+(-{0,1}\d+(\.\d+)?)')
		
class DinFile:
	def __init__(self, filename):
		self.file = open(filename, 'w', encoding='utf-8')
	
	def writeln(self, text):
		self.file.write(text+"\n")
	
	def close(self):
		self.file.close()
		
class StoutFile:
	def writeln(self, text):
		print(text)
	
	def close(self):
		logging.debug('closing stout file')

class StoutAndDinFile(DinFile, StoutFile):
	def writeln(self, text):
		DinFile.writeln(self, text)
		StoutFile.writeln(self, text)

class Processor:
	def __init__(self, line_number_start, line_number_step, no_comments):
		self.num_steps = line_number_step
		self.num_start = line_number_start
		self.no_comments = no_comments
		self.rapid = False
		self.fedrate = None
		self.line_number = line_number_start
		self.circle = False
		self.circle_center_x = 0
		self.circle_center_y = 0
		self.circle_center_z = 0
		self.circle_dir = 1
		self.x = 0
		self.y = 0
		self.z = 0
	
	def transform(self, file, out):
		with open(file, encoding='utf-8') as infile:
			lines = infile.readlines()
			max_line_number = len(lines) * self.num_steps + self.num_start
			line_number_size = len(str(max_line_number))
			line_number_format = "N{0:0"+str(line_number_size)+"d}"
			logging.debug("max line number: "+str(max_line_number))
			logging.debug("using number offset: "+str(line_number_size))
			fromatted_line_number=line_number_format.format(self.line_number)
			out.writeln(fromatted_line_number+' G90 G71')
			self.line_number += self.num_steps
			linebuffer = ''
			for line in lines:
				if line[-2:] == '$\n':
					linebuffer = line[0:-2].strip()
					continue
				else:
					line = linebuffer + ' ' + line.strip()
					line = line.strip()
					linebuffer = ''
				fromatted_line_number=line_number_format.format(self.line_number)
				goto_result = goto_pattern.match(line)
				if goto_result:
					last_x = self.x
					last_y = self.y
					last_z = self.z
					self.x = float(goto_result.group(1))
					self.y = float(goto_result.group(3))
					self.z = float(goto_result.group(5))
					if self.circle:
						self.circle = False
						self.i = self.circle_center_x - last_x
						self.j = self.circle_center_y - last_y
						self.k = self.circle_center_z - last_z
						if self.circle_dir == 1:
							gcode = 'G03'
						else:
							gcode = 'G02'
						out.writeln(fromatted_line_number+' '+gcode+' X'+str(self.x)+' Y'+str(self.y)+' Z'+str(self.z)+' I'+str(self.i)+' J'+str(self.j)+' K'+str(self.k))
					else:
						if self.rapid:
							gcode = 'G00'
							self.rapid = False
						else:
							gcode = 'G01'
						out.writeln(fromatted_line_number+' '+gcode+' X'+str(self.x)+' Y'+str(self.y)+' Z'+str(self.z))
					self.line_number += self.num_steps
					continue
				
				if rapid_pattern.match(line):
					self.rapid = True
					continue
				
				loadtl_result = loadtl_pattern.match(line)
				if loadtl_result:
					out.writeln(fromatted_line_number+' T'+loadtl_result.group(1)+' M6')
					self.line_number += self.num_steps
					continue
					
				fedrat_result = fedrat_pattern.match(line)
				if fedrat_result:
					if float(fedrat_result.group(1)) == self.fedrate:
						continue
					self.fedrate = float(fedrat_result.group(1))
					out.writeln(fromatted_line_number+' F'+str(self.fedrate))
					self.line_number += self.num_steps
					continue
					
				circle_result = circle_pattern.match(line)
				if circle_result:
					print('CIRCLE '+line)
					self.circle_center_x = float(circle_result.group(1))
					self.circle_center_y = float(circle_result.group(3))
					self.circle_center_z = float(circle_result.group(5))
					c1 = float(circle_result.group(7))
					c2 = float(circle_result.group(9))
					self.circle_dir = float(circle_result.group(11))
					self.r = float(circle_result.group(13))
					if not self.no_comments:
						out.writeln('( circle radius: '+str(self.r)+')')
					if c1 != 0 or c2 != 0:
						raise Exception('the unknown values of CIRCLE are not zero c1: '+str(c1)+', c2: '+str(c2))
					self.circle = True
					continue
				
				if not self.no_comments:
					out.writeln('( unprocessed: '+line.strip()+')')
				logging.info('unprocessed: '+line.strip())

					
			fromatted_line_number=line_number_format.format(self.line_number)
			out.writeln(fromatted_line_number+' M30')
		
		out.close()
	
if __name__ == "__main__":
	args = parser.parse_args()
	logging.raiseExceptions = False
	
	if args.output and args.dir:
		print('arguments -d and -o are illigal')
		exit(1)
		
	log_format = '%(levelname)s: %(message)s'
	if args.verbose == 2:
		logging.basicConfig(format=log_format, level=logging.DEBUG)
	elif args.verbose == 1:
		logging.basicConfig(format=log_format, level=logging.INFO)
	else:
		logging.basicConfig(format=log_format, level=logging.WARNING)
	
	if os.path.isdir(args.file):
		file_list = []
		if args.output:
			logging.warning('ignoring output file ' + args.output)
		if args.recursive:
			logging.info('searching recursive in directory '+os.path.abspath(args.file))
			for root, subFolders, files in os.walk(args.file):
				for filename in files:
					clfile_result = clfile_pattern.match(filename)
					if clfile_result:
						file_list.append((os.path.join(root, filename), os.path.join(root, clfile_result.group(1)), int(clfile_result.group(2))))
		else:
			logging.info('searching in directory '+os.path.abspath(args.file))
			for filename in os.listdir(args.file):
				clfile_result = clfile_pattern.match(filename)
				if clfile_result:
					file_list.append((os.path.join(args.file, filename), os.path.join(args.file, clfile_result.group(1)), clfile_result.group(2)))
		
		logging.debug('file list: '+str(file_list))
		
		'''
		only transform the last file (highest file file extension)
		'''
		done_list = []
		todo_list = []
		for x in file_list:
			if x[1] in done_list:
				continue
			max = x
			for y in file_list:
				if x[0] == y[0]:
					continue
				if x[1] == y[1] and y[2] > max[2]:
					max = y
			done_list.append(x[1])
			todo_list.append(max)
		
		logging.debug('todo list: '+str(todo_list))
		
		if not len(todo_list):
			logging.warning('could not find any Pro/CLfile in '+os.path.abspath(args.file))
			
		for item in todo_list:
			target = item[1]+'.'+args.file_extension
			if not args.force and os.path.exists(target):
				logging.warning('file '+target+' exists! skipping '+item[0])
				continue
			logging.info('processing file '+item[0]+' -> '+target)
			p = Processor(args.num_start, args.num_steps, args.no_comments)
			p.transform(item[0], DinFile(target))
				
	else:
		if args.verbose:
			if args.output:
				out = StoutAndDinFile(args.output)
			else:
				logging.warning('Writing log and G-Codes to stout')
				out = StoutFile()
		else:
			if args.output:
				out = DinFile(args.output)
			else:
				out = StoutFile()
		p = Processor(args.num_start, args.num_steps, args.no_comments)
		p.transform(args.file, out)
	