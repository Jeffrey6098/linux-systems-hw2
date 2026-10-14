
import os
import shlex
import signal
import sys



class Job:

  def __init__(self, pid, command, background):
    self.pid = pid
    self.command = command
    self.background = background
    self.status = "Running"  # Running, Stopped, Done


jobs = {}  # Maps job_id (int) -> Job object
next_job_id = 1  # Tracks the next available job ID



def reap_children():
  while True:
    try:
     
      pid, status = os.waitpid(-1, os.WNOHANG)
    except ChildProcessError:
       break

    if pid == 0:
      
      break

   
    for job in jobs.values():
      if job.pid == pid:
        job.status = "Done"
        break



def parse_command(line):

  try:
    tokens = shlex.split(line)
  except ValueError as e:
    print(f"myshell: parse error: {e}")
    return [], "", False

  if not tokens:
    return [], "", False

  is_background = False

  if tokens[-1] == "&":
    is_background = True
    tokens.pop()
 
  elif tokens[-1].endswith("&"):
    is_background = True
    tokens[-1] = tokens[-1][:-1]

  
  if not tokens:
    return [], "", False

  
  command_str = " ".join(tokens)

  return tokens, command_str, is_background



def handle_builtin(tokens):
  
  cmd = tokens[0]

  if cmd == "exit":
    sys.exit(0)

  elif cmd == "cd":
   
    target_dir = tokens[1] if len(tokens) > 1 else os.path.expanduser("~")
    try:
      os.chdir(target_dir)
    except FileNotFoundError:
      print(f"myshell: cd: {target_dir}: No such file or directory")
    except NotADirectoryError:
      print(f"myshell: cd: {target_dir}: Not a directory")
    except PermissionError:
      print(f"myshell: cd: {target_dir}: Permission denied")
    return True

  elif cmd == "jobs":
   
    for job_id, job in list(jobs.items()):
      print(f"[{job_id}]  {job.status:<10} {job.command}")
      if job.status == "Done":
        del jobs[job_id]
    return True

  elif cmd == "fg":
    if len(tokens) < 2:
      print("myshell: fg: job id required")
      return True

    try:
      job_id = int(tokens[1].lstrip("%"))
    except ValueError:
      print(f"myshell: fg: {tokens[1]}: no such job")
      return True

    job = jobs.get(job_id)
    if not job:
      print(f"myshell: fg: {tokens[1]}: no such job")
      return True

    
    print(job.command)

    
    if job.status == "Running":
      try:
        os.waitpid(job.pid, 0)
      except ChildProcessError:
        pass
      except KeyboardInterrupt:
        
        print()

    del jobs[job_id]
    return True

  elif cmd == "kill":
    if len(tokens) < 2:
      print("myshell: kill: job id required")
      return True

    try:
      job_id = int(tokens[1].lstrip("%"))
    except ValueError:
      print(f"myshell: kill: {tokens[1]}: no such job")
      return True

    job = jobs.get(job_id)
    if not job:
      print(f"myshell: kill: {tokens[1]}: no such job")
      return True

    try:
      
      os.kill(job.pid, signal.SIGTERM)
     
      os.waitpid(job.pid, 0)
    except (ProcessLookupError, ChildProcessError):
      pass

    print(f"[{job_id}]  Terminated  {job.command}")
    del jobs[job_id]
    return True

  return False  


def execute_external(tokens, command_str, is_background):

  global next_job_id

  try:
    pid = os.fork()
  except OSError as e:
    print(f"myshell: fork failed: {e}")
    return


  if pid == 0:
    try:
      os.execvp(tokens[0], tokens)
    except FileNotFoundError:
      print(f"myshell: {tokens[0]}: command not found")
    except OSError as e:
      print(f"myshell: {tokens[0]}: {e.strerror}")

    os._exit(1)


  else:
    if is_background:
      jobs[next_job_id] = Job(pid, command_str, True)

      print(f"[{next_job_id}] {pid} {command_str}")
      next_job_id += 1
    else:
      try:
        os.waitpid(pid, 0)
      except ChildProcessError:
        pass
      except KeyboardInterrupt:
       
        print()


def main():
  while True:
    
    reap_children()

    try:
    
      line = input("myshell> ")
    except EOFError:
    
      print()
      break
    except KeyboardInterrupt:
    
      print()
      continue

   
    reap_children()

 
    tokens, command_str, is_background = parse_command(line)
    if not tokens:
      continue

    
    if not handle_builtin(tokens):
      execute_external(tokens, command_str, is_background)

   
    reap_children()


if __name__ == "__main__":
  main()