
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <math.h>
#include "usb_serial.h"
#include "HardwareSerial.h"
#include "wiring.h"
#include "functions.h"
#include "stepper.h"
#include "tcl_interpreter.h"
// #define DEBUG 1


extern uint8_t spi_error;
extern enum LED_MODES led_mode;

char inString[MAX_STRING_LENGTH];                             // inputbuffer for the USB
char buf[MAX_STRING_LENGTH];                                  // buffer to generate output strings

static char tempBuffer[MAX_STRING_LENGTH];                    // temporary input buffer for the USB
static unsigned short anzByte;                                // count the bytes in the tempBuffer, receiver status

struct tcl tcl;

static int tcl_is_special(char c, int q) {
  return (c == '$' || (!q && (c == '{' || c == '}' || c == ';' || c == '\r' ||
                              c == '\n')) ||
          c == '[' || c == ']' || c == '"' || c == '\0');
}

static int tcl_is_space(char c) { return (c == ' ' || c == '\t'); }

static int tcl_is_end(char c) {
  return (c == '\n' || c == '\r' || c == ';' || c == '\0');
}

int tcl_next(const char *s, size_t n, const char **from, const char **to,
             int *q) {
  unsigned int i = 0;
  int depth = 0;
  char open;
  char close;

#ifdef DEBUG
  sprintf(buf, "tcl_next(%.*s)+%d+%d|%d", n, s, *from - s, *to - s, *q);
  printLine(buf);
#endif

  /* Skip leading spaces if not quoted */
  for (; !*q && n > 0 && tcl_is_space(*s); s++, n--) {
  }
  *from = s;
  /* Terminate command if not quoted */
  if (!*q && n > 0 && tcl_is_end(*s)) {
    *to = s + 1;
    return TCMD;
  }
  if (*s == '$') { /* Variable token, must not start with a space or quote */
    if (tcl_is_space(s[1]) || s[1] == '"') {
      return TERROR;
    }
    int mode = *q;
    *q = 0;
    int r = tcl_next(s + 1, n - 1, to, to, q);
    *q = mode;
    return ((r == TWORD && *q) ? TPART : r);
  }

  if (*s == '[' || (!*q && *s == '{')) {
    /* Interleaving pairs are not welcome, but it simplifies the code */
    open = *s;
    close = (open == '[' ? ']' : '}');
    for (i = 0, depth = 1; i < n && depth != 0; i++) {
      if (i > 0 && s[i] == open) {
        depth++;
      } else if (s[i] == close) {
        depth--;
      }
    }
  } else if (*s == '"') {
    *q = !*q;
    *from = *to = s + 1;
    if (*q) {
      return TPART;
    }
    if (n < 2 || (!tcl_is_space(s[1]) && !tcl_is_end(s[1]))) {
      return TERROR;
    }
    *from = *to = s + 1;
    return TWORD;
  } else {
    while (i < n && (*q || !tcl_is_space(s[i])) && !tcl_is_special(s[i], *q)) {
      i++;
    }
  }
  *to = s + i;
  if (i == n) {
    return TERROR;
  }
  if (*q) {
    return TPART;
  }
  return (tcl_is_space(s[i]) || tcl_is_end(s[i])) ? TWORD : TPART;
}

const char *tcl_string(tcl_value_t *v) { return v; }
unsigned long tcl_ulong(tcl_value_t *v) { return strtoul(v, (char **)NULL, (int)NULL); }
int tcl_int(tcl_value_t *v) { return atoi(v); }
int tcl_length(tcl_value_t *v) { return v == NULL ? 0 : strlen(v); }

void tcl_free(tcl_value_t *v) { free(v); }

tcl_value_t *tcl_append_string(tcl_value_t *v, const char *s, size_t len) {
  size_t n = tcl_length(v);
  v = realloc(v, n + len + 1);
  memset((char *)tcl_string(v) + n, 0, len + 1);
  strncpy((char *)tcl_string(v) + n, s, len);
  return v;
}

tcl_value_t *tcl_append(tcl_value_t *v, tcl_value_t *tail) {
  v = tcl_append_string(v, tcl_string(tail), tcl_length(tail));
  tcl_free(tail);
  return v;
}

tcl_value_t *tcl_alloc(const char *s, size_t len) {
  return tcl_append_string(NULL, s, len);
}

tcl_value_t *tcl_dup(tcl_value_t *v) {
  return tcl_alloc(tcl_string(v), tcl_length(v));
}

tcl_value_t *tcl_list_alloc() { return tcl_alloc("", 0); }

int tcl_list_length(tcl_value_t *v) {
  int count = 0;
  tcl_each(tcl_string(v), tcl_length(v) + 1, 0) {
    if (p.token == TWORD) {
      count++;
    }
  }
  return count;
}

void tcl_list_free(tcl_value_t *v) { free(v); }

tcl_value_t *tcl_list_at(tcl_value_t *v, int index) {
  int i = 0;
  tcl_each(tcl_string(v), tcl_length(v) + 1, 0) {
    if (p.token == TWORD) {
      if (i == index) {
        if (p.from[0] == '{') {
          return tcl_alloc(p.from + 1, p.to - p.from - 2);
        }
        return tcl_alloc(p.from, p.to - p.from);
      }
      i++;
    }
  }
  return NULL;
}

tcl_value_t *tcl_list_append(tcl_value_t *v, tcl_value_t *tail) {
  if (tcl_length(v) > 0) {
    v = tcl_append(v, tcl_alloc(" ", 2));
  }
  if (tcl_length(tail) > 0) {
    int q = 0;
    const char *p;
    for (p = tcl_string(tail); *p; p++) {
      if (tcl_is_space(*p) || tcl_is_special(*p, 0)) {
        q = 1;
        break;
      }
    }
    if (q) {
      v = tcl_append(v, tcl_alloc("{", 1));
    }
    v = tcl_append(v, tcl_dup(tail));
    if (q) {
      v = tcl_append(v, tcl_alloc("}", 1));
    }
  } else {
    v = tcl_append(v, tcl_alloc("{}", 2));
  }
  return v;
}

static struct tcl_env *tcl_env_alloc(struct tcl_env *parent) {
  struct tcl_env *env = malloc(sizeof(*env));
  env->vars = NULL;
  env->parent = parent;
  return env;
}

static struct tcl_var *tcl_env_var(struct tcl_env *env, tcl_value_t *name) {
  struct tcl_var *var = malloc(sizeof(struct tcl_var));
  var->name = tcl_dup(name);
  var->next = env->vars;
  var->value = tcl_alloc("", 0);
  env->vars = var;
  return var;
}

static struct tcl_env *tcl_env_free(struct tcl_env *env) {
  struct tcl_env *parent = env->parent;
  while (env->vars) {
    struct tcl_var *var = env->vars;
    env->vars = env->vars->next;
    tcl_free(var->name);
    tcl_free(var->value);
    free(var);
  }
  free(env);
  return parent;
}

tcl_value_t *tcl_var(struct tcl *tcl, tcl_value_t *name, tcl_value_t *v) {
#ifdef DEBUG
  sprintf(buf, "var(%s := %.*s)", tcl_string(name), tcl_length(v), tcl_string(v));
  printLine(buf);
#endif
  struct tcl_var *var;
  for (var = tcl->env->vars; var != NULL; var = var->next) {
    if (strcmp(var->name, tcl_string(name)) == 0) {
      break;
    }
  }
  if (var == NULL) {
    var = tcl_env_var(tcl->env, name);
  }
  if (v != NULL) {
    tcl_free(var->value);
    var->value = tcl_dup(v);
    tcl_free(v);
  }
  return var->value;
}

int tcl_result(struct tcl *tcl, int flow, tcl_value_t *result) {
#ifdef DEBUG
  sprintf(buf, "tcl_result %.*s, flow=%d", tcl_length(result), tcl_string(result), flow);
  printLine(buf);
#endif
  tcl_free(tcl->result);
  tcl->result = result;
  return flow;
}

int tcl_subst(struct tcl *tcl, const char *s, size_t len) {
#ifdef DEBUG
  sprintf(buf, "subst(%.*s)", (int)len, s);
  printLine(buf);
#endif
  if (len == 0) {
    return tcl_result(tcl, FNORMAL, tcl_alloc("", 0));
  }
  switch (s[0]) {
  case '{':
    if (len <= 1) {
      return tcl_result(tcl, FERROR, tcl_alloc("", 0));
    }
    return tcl_result(tcl, FNORMAL, tcl_alloc(s + 1, len - 2));
  case '$': {
    if (len >= MAX_VAR_LENGTH) {
      return tcl_result(tcl, FERROR, tcl_alloc("", 0));
    }
    char buf[5 + MAX_VAR_LENGTH] = "set ";
    strncat(buf, s + 1, len - 1);
    return tcl_eval(tcl, buf, strlen(buf) + 1);
  }
  case '[': {
    tcl_value_t *expr = tcl_alloc(s + 1, len - 2);
    int r = tcl_eval(tcl, tcl_string(expr), tcl_length(expr) + 1);
    tcl_free(expr);
    return r;
  }
  default:
    return tcl_result(tcl, FNORMAL, tcl_alloc(s, len));
  }
}

int tcl_eval(struct tcl *tcl, const char *s, size_t len) {
#ifdef DEBUG
  sprintf(buf, "eval(%.*s)->", (int)len, s);
  printLine(buf);
#endif
  tcl_value_t *list = tcl_list_alloc();
  tcl_value_t *cur = NULL;
  tcl_each(s, len, 1) {
#ifdef DEBUG
    sprintf(buf, "tcl_next %d %.*s", p.token, (int)(p.to - p.from), p.from);
    printLine(buf);
#endif
    switch (p.token) {
    case TERROR:
#ifdef DEBUG
      sprintf(buf, "eval: FERROR, lexer error");
      printLine(buf);
#endif
      return tcl_result(tcl, FERROR, tcl_alloc("", 0));
    case TWORD:
#ifdef DEBUG
      sprintf(buf, "token %.*s, length=%d, cur=%p (3.1.1)", (int)(p.to - p.from), p.from, (int)(p.to - p.from), cur);
      printLine(buf);
#endif
      if (cur != NULL) {
        tcl_subst(tcl, p.from, p.to - p.from);
        tcl_value_t *part = tcl_dup(tcl->result);
        cur = tcl_append(cur, part);
      } else {
        tcl_subst(tcl, p.from, p.to - p.from);
        cur = tcl_dup(tcl->result);
      }
      list = tcl_list_append(list, cur);
      tcl_free(cur);
      cur = NULL;
      break;
    case TPART:
      tcl_subst(tcl, p.from, p.to - p.from);
      tcl_value_t *part = tcl_dup(tcl->result);
      cur = tcl_append(cur, part);
      break;
    case TCMD:
      if (tcl_list_length(list) == 0) {
        tcl_result(tcl, FNORMAL, tcl_alloc("", 0));
      } else {
        tcl_value_t *cmdname = tcl_list_at(list, 0);
        struct tcl_cmd *cmd = NULL;
        int r = FERROR;
        for (cmd = tcl->cmds; cmd != NULL; cmd = cmd->next) {
          if (strcmp(tcl_string(cmdname), tcl_string(cmd->name)) == 0) {
            if (cmd->arity == 0 || cmd->arity == tcl_list_length(list)) {
              r = cmd->fn(tcl, list, cmd->arg);
              break;
            }
          }
        }
        tcl_free(cmdname);
        if (cmd == NULL || r != FNORMAL) {
          tcl_list_free(list);
          return r;
        }
      }
      tcl_list_free(list);
      list = tcl_list_alloc();
      break;
    }
  }
  tcl_list_free(list);
  return FNORMAL;
}

/* --------------------------------- */
/* --------------------------------- */
/* --------------------------------- */
/* --------------------------------- */
/* --------------------------------- */
void tcl_register(struct tcl *tcl, const char *name, tcl_cmd_fn_t fn, int arity,
                  void *arg) {
  struct tcl_cmd *cmd = malloc(sizeof(struct tcl_cmd));
  cmd->name = tcl_alloc(name, strlen(name));
  cmd->fn = fn;
  cmd->arg = arg;
  cmd->arity = arity;
  cmd->next = tcl->cmds;
  tcl->cmds = cmd;
}

static int tcl_cmd_set(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  tcl_value_t *var = tcl_list_at(args, 1);
  tcl_value_t *val = tcl_list_at(args, 2);
  int r = tcl_result(tcl, FNORMAL, tcl_dup(tcl_var(tcl, var, val)));
  tcl_free(var);
  return r;
}

static int tcl_cmd_subst(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  tcl_value_t *s = tcl_list_at(args, 1);
  int r = tcl_subst(tcl, tcl_string(s), tcl_length(s));
  tcl_free(s);
  return r;
}

static int tcl_cmd_puts(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  tcl_value_t *text = tcl_list_at(args, 1);
  printLine(tcl_string(text));
  return tcl_result(tcl, FNORMAL, text);
}

static int tcl_user_proc(struct tcl *tcl, tcl_value_t *args, void *arg) {
  tcl_value_t *code = (tcl_value_t *)arg;
  tcl_value_t *params = tcl_list_at(code, 2);
  tcl_value_t *body = tcl_list_at(code, 3);
  tcl->env = tcl_env_alloc(tcl->env);
  for (int i = 0; i < tcl_list_length(params); i++) {
    tcl_value_t *param = tcl_list_at(params, i);
    tcl_value_t *v = tcl_list_at(args, i + 1);
    tcl_var(tcl, param, v);
    tcl_free(param);
  }
  tcl_eval(tcl, tcl_string(body), tcl_length(body) + 1);
  tcl->env = tcl_env_free(tcl->env);
  tcl_free(params);
  tcl_free(body);
  return FNORMAL;
}

static int tcl_cmd_proc(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  tcl_value_t *name = tcl_list_at(args, 1);
  tcl_register(tcl, tcl_string(name), tcl_user_proc, 0, tcl_dup(args));
  tcl_free(name);
  return tcl_result(tcl, FNORMAL, tcl_alloc("", 0));
}

static int tcl_cmd_if(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  int i = 1;
  int n = tcl_list_length(args);
  int r = FNORMAL;
  while (i < n) {
    tcl_value_t *cond = tcl_list_at(args, i);
    tcl_value_t *branch = NULL;
    if (i + 1 < n) {
      branch = tcl_list_at(args, i + 1);
    }
    r = tcl_eval(tcl, tcl_string(cond), tcl_length(cond) + 1);
    tcl_free(cond);
    if (r != FNORMAL) {
      tcl_free(branch);
      break;
    }
    if (tcl_int(tcl->result)) {
      r = tcl_eval(tcl, tcl_string(branch), tcl_length(branch) + 1);
      tcl_free(branch);
      break;
    }
    i = i + 2;
    tcl_free(branch);
  }
  return r;
}

static int tcl_cmd_flow(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  int r = FERROR;
  tcl_value_t *flowval = tcl_list_at(args, 0);
  const char *flow = tcl_string(flowval);
  if (strcmp(flow, "break") == 0) {
    r = FBREAK;
  } else if (strcmp(flow, "continue") == 0) {
    r = FAGAIN;
  } else if (strcmp(flow, "return") == 0) {
    r = tcl_result(tcl, FRETURN, tcl_list_at(args, 1));
  }
  tcl_free(flowval);
  return r;
}

static int tcl_cmd_while(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  tcl_value_t *cond = tcl_list_at(args, 1);
  tcl_value_t *loop = tcl_list_at(args, 2);
  int r;
  for (;;) {
    r = tcl_eval(tcl, tcl_string(cond), tcl_length(cond) + 1);
    if (r != FNORMAL) {
      tcl_free(cond);
      tcl_free(loop);
      return r;
    }
    if (!tcl_int(tcl->result)) {
      tcl_free(cond);
      tcl_free(loop);
      return FNORMAL;
    }
    int r = tcl_eval(tcl, tcl_string(loop), tcl_length(loop) + 1);
    switch (r) {
    case FBREAK:
      tcl_free(cond);
      tcl_free(loop);
      return FNORMAL;
    case FRETURN:
      tcl_free(cond);
      tcl_free(loop);
      return FRETURN;
    case FAGAIN:
      continue;
    case FERROR:
      tcl_free(cond);
      tcl_free(loop);
      return FERROR;
    }
  }
}

static int tcl_cmd_math(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  char buf[64];
  tcl_value_t *opval = tcl_list_at(args, 0);
  tcl_value_t *aval = tcl_list_at(args, 1);
  tcl_value_t *bval = tcl_list_at(args, 2);
  const char *op = tcl_string(opval);
  int a = tcl_int(aval);
  int b = tcl_int(bval);
  int c = 0;
  if (op[0] == '+') {
    c = a + b;
  } else if (op[0] == '-') {
    c = a - b;
  } else if (op[0] == '*') {
    c = a * b;
  } else if (op[0] == '/') {
    c = a / b;
  } else if (op[0] == '>' && op[1] == '\0') {
    c = a > b;
  } else if (op[0] == '>' && op[1] == '=') {
    c = a >= b;
  } else if (op[0] == '<' && op[1] == '\0') {
    c = a < b;
  } else if (op[0] == '<' && op[1] == '=') {
    c = a <= b;
  } else if (op[0] == '=' && op[1] == '=') {
    c = a == b;
  } else if (op[0] == '!' && op[1] == '=') {
    c = a != b;
  }

  char *p = buf + sizeof(buf) - 1;
  char neg = (c < 0);
  *p-- = 0;
  if (neg) {
    c = -c;
  }
  do {
    *p-- = '0' + (c % 10);
    c = c / 10;
  } while (c > 0);
  if (neg) {
    *p-- = '-';
  }
  p++;

  tcl_free(opval);
  tcl_free(aval);
  tcl_free(bval);
  return tcl_result(tcl, FNORMAL, tcl_alloc(p, strlen(p)));
}


/*
 *    reset                              reset Teensy interface status
 */
static int tcl_cmd_reset(struct tcl *tcl, tcl_value_t *args, void *arg)
{
   (void) arg;
   char buf[64] = "";
   LED_OFF;
   led_mode = LED_STATUS;
   step_reset();
   return tcl_result(tcl, FNORMAL, tcl_alloc(buf, strlen(buf)));
}

/*
 *    ?                                   Help
 */
static int tcl_cmd_help(struct tcl *tcl, tcl_value_t *args, void *arg)
{
  (void)arg;
  print_help();
  return tcl_result(tcl, FNORMAL, tcl_alloc("", 0));
}

/*
 *    v?                                  Firmware Version
 */
static int tcl_cmd_fw_version(struct tcl *tcl, tcl_value_t *args, void *arg) {
  (void)arg;
  print_fw_version();
  return tcl_result(tcl, FNORMAL, tcl_alloc("", 0));
}



/*
 *    led <cmd> [<value>]                 print/set Teensy LED mode
 *
 *    led get_mode                        print Teensy LED mode
 *    led set_mode <value>                set Teensy LED mode
 *    led wakeup                          only in led_stby mode: wakeup and stay
 *    led wakeup <value>                  only in led_stby mode: wakeup for <value>: 1-1000000 us
 *    led sleep                           only in led_stby mode: sleep and stay
 *    led sleep <value>                   only in led_stby mode: sleep for <value>: 1-1000000 us
 */
static int tcl_cmd_led(struct tcl *tcl, tcl_value_t *args, void *arg)
{
  (void)arg;
  char buf[64] = "";
  tcl_value_t *cmd = tcl_list_at(args, 1);
  tcl_value_t *val = tcl_list_at(args, 2);

  if (cmd && !strcmp ("get_mode", cmd) && !val)
  {
     if (led_mode == LED_STBY)
        sprintf(buf, "led_stby");
     else sprintf(buf, "led_status");
     tcl_free(cmd);
  }
  else if (cmd && !strcmp ("set_mode", cmd) && val && !strcmp ("led_stby", val))
  {
    led_mode = LED_STBY;
    LED_CONFIG; LED_ON; // default is ON
    tcl_free(cmd); tcl_free(val);
  }
  else if (cmd && !strcmp ("set_mode", cmd) && val && !strcmp ("led_status", val))
  {
    led_mode = LED_STATUS;
    tcl_free(cmd); tcl_free(val);
  }
  else if (cmd && !strcmp ("wakeup", cmd) && !val)
  {
    tcl_free(cmd);
    if (led_mode == LED_STBY)
    {
      LED_ON;
    } else {
      return tcl_result(tcl, FERROR, tcl_alloc("not in led_stby mode", strlen("not in led_stby mode")));
    }
  }
  else if (cmd && !strcmp ("wakeup", cmd) && val && (tcl_ulong(val) > 0) && (tcl_ulong(val) <= 1000))
  {
    tcl_free(cmd);
    unsigned long time_ms = tcl_ulong(val); tcl_free(val);
    if (led_mode == LED_STBY) 
    {
      LED_ON;
      delay(time_ms);
      LED_OFF;
    } else {
      return tcl_result(tcl, FERROR, tcl_alloc("not in led_stby mode", strlen("not in led_stby mode")));
    }
  }
  else if (cmd && !strcmp ("sleep", cmd) && !val)
  {
    tcl_free(cmd);
    if (led_mode == LED_STBY) 
    { 
      LED_OFF;
    } else {
      return tcl_result(tcl, FERROR, tcl_alloc("not in led_stby mode", strlen("not in led_stby mode")));
    }   
  }
  else if (cmd && !strcmp ("sleep", cmd) && val && (tcl_ulong(val) > 0) && (tcl_ulong(val) <= 1000))
  {
    tcl_free(cmd);
    unsigned long time_ms = tcl_ulong(val); tcl_free(val);
    if (led_mode == LED_STBY) 
    {
      LED_OFF;
      delay(time_ms);
      LED_ON;
    } else {
      return tcl_result(tcl, FERROR, tcl_alloc("not in led_stby mode", strlen("not in led_stby mode")));
    }
  } else {
    if (cmd) tcl_free(cmd); if (val) tcl_free(cmd);
    return tcl_result(tcl, FERROR, tcl_alloc("Invalid arguments to 'led' command", strlen("Invalid arguments to 'led' command")));  
  }
  return tcl_result(tcl, FNORMAL, tcl_alloc(buf, strlen(buf)));
}

void tcl_destroy(struct tcl *tcl) {
  while (tcl->env) {
    tcl->env = tcl_env_free(tcl->env);
  }
  while (tcl->cmds) {
    struct tcl_cmd *cmd = tcl->cmds;
    tcl->cmds = tcl->cmds->next;
    tcl_free(cmd->name);
    free(cmd->arg);
    free(cmd);
  }
  tcl_free(tcl->result);
}

//
// ===========================================================================
// own functions:


static int tcl_cmd_step(struct tcl *tcl, tcl_value_t *args, void *arg) {
    (void)arg;
    char buf[64] = "";
    tcl_value_t *cmd = tcl_list_at(args, 1);
    tcl_value_t *val = tcl_list_at(args, 2);
    int value = tcl_int(val);
  
    if (cmd && !strcmp ("get_pos", cmd) && !val) {
        value=step_get();
        sprintf(buf, "position = %d", value);
        tcl_free(cmd);
    }else if (cmd && !strcmp ("set_pos", cmd) && val) {
        step_moveto(value);
        sprintf(buf, "set position = %d", value);
        tcl_free(cmd); tcl_free(val);
    }else if (cmd && !strcmp ("get_enable", cmd) && !val) {
        value=step_getenable();
        sprintf(buf, "enable = %d", value);
        tcl_free(cmd);
    }else if (cmd && !strcmp ("set_enable", cmd) && val) {
        step_setenable(value);
        sprintf(buf, "set enable = %d", value);
        tcl_free(cmd); tcl_free(val);
    }else if (cmd && !strcmp ("get_speed", cmd) && !val) {
        value=step_getspeed();
        sprintf(buf, "speed = %d", value);
        tcl_free(cmd);
    }else if (cmd && !strcmp ("set_speed", cmd) && val) {
        step_setspeed(value);
        sprintf(buf, "set speed = %d", value);
        tcl_free(cmd); tcl_free(val);   
    }else if (cmd && !strcmp ("get_acceleration", cmd) && !val) {
        value=step_getacceleration();
        sprintf(buf, "acceleration = %d", value);
        tcl_free(cmd);
    }else if (cmd && !strcmp ("set_acceleration", cmd) && val) {
        step_setacceleration(value);
        sprintf(buf, "set acceleration = %d", value);
        tcl_free(cmd); tcl_free(val);  
    }else if (cmd && !strcmp ("running", cmd) && !val) {
        value=step_running();
        sprintf(buf, "running = %d", value);
        tcl_free(cmd);             
    } else {
        if (cmd) tcl_free(cmd); if (val) tcl_free(val);
        return tcl_result(tcl, FERROR, tcl_alloc("Invalid arguments to 'step' command", strlen("Invalid arguments to 'step' command")));  
  }
  return tcl_result(tcl, FNORMAL, tcl_alloc(buf, strlen(buf)));
}



//
// ===========================================================================
//
/*
 *    Main initialisation routine for tcl_interpreter
*/
void tcl_init(struct tcl *tcl) {
  tcl->env = tcl_env_alloc(NULL);
  tcl->result = tcl_alloc("", 0);
  tcl->cmds = NULL;
  tcl_register(tcl, "set", tcl_cmd_set, 0, NULL);
  tcl_register(tcl, "subst", tcl_cmd_subst, 2, NULL);
  tcl_register(tcl, "puts", tcl_cmd_puts, 2, NULL);
  tcl_register(tcl, "proc", tcl_cmd_proc, 4, NULL);
  tcl_register(tcl, "if", tcl_cmd_if, 0, NULL);
  tcl_register(tcl, "while", tcl_cmd_while, 3, NULL);
  tcl_register(tcl, "return", tcl_cmd_flow, 0, NULL);
  tcl_register(tcl, "break", tcl_cmd_flow, 1, NULL);
  tcl_register(tcl, "continue", tcl_cmd_flow, 1, NULL);
  char *math[] = {"+", "-", "*", "/", ">", ">=", "<", "<=", "==", "!="};
  for (unsigned int i = 0; i < (sizeof(math) / sizeof(math[0])); i++) {
    tcl_register(tcl, math[i], tcl_cmd_math, 3, NULL);
  }
  tcl_register(tcl, "reset", tcl_cmd_reset, 0, NULL);
  tcl_register(tcl, "?", tcl_cmd_help, 0, NULL);
  tcl_register(tcl, "v?", tcl_cmd_fw_version, 0, NULL);
  tcl_register(tcl, "led", tcl_cmd_led, 0, NULL);
  
//own functions:
  tcl_register(tcl, "step", tcl_cmd_step, 0, NULL);
}

//
// parse a user command and execute it, or print an error message
//
void parse_and_execute_command(short len)
{
   int r = tcl_eval(&tcl, inString, len+1);

   if (*tcl.result) 
      printLine (tcl_string(tcl.result));

   if (r != FERROR) {
      printLine ("$OK");
   } else {
      printLine ("$Error");
   }
}

/*------------------------------------------------------------------------------
//::FUNCTION:printLine
------------------------------------------------------------------------------*/

//------------------------------------------------------------------------------
//  DESCRIPTION:
//  ~~~~~~~~~~~~
/** \brief print out a string and add \r\n
 *
 *  \param *string pointer to the string
 */
/*----------------------------------------------------------------------------*/
void printLine(const char *string)
{
   //send char by char until the termination 0 
   while(*string != 0)
   {
      usb_serial_putchar(*(string++));
   }
   usb_serial_putchar(0x0D);
   usb_serial_putchar(0x0A);
}

void prints(const char *string)
{
   //send char by char until the termination 0 
   while(*string != 0)
   {
      usb_serial_putchar(*(string++));
   }
}


// Receive a string from the USB serial port.  The string is stored
// in the buffer and this function will not exceed the buffer size.
// A carriage return or newline completes the string, and is not
// stored into the buffer.
// The return value is the number of characters received, or 255 if
// the virtual serial connection was closed while waiting.
//
int16_t check_recv(void)
{
   int16_t r, n;

   // is there a new character available ?
   r = usb_serial_getchar();
   // if yes -> check
   if (r != -1) {
      // if we receive a CR
      if (r == '\r' || r == '\n' || anzByte >= MAX_STRING_LENGTH-1)
      {
         // terminate the string with a 0
         tempBuffer[anzByte] = 0;
         // copy the data to accept new input
         strcpy (inString, tempBuffer);
         // reset the buffer to receive char
         n = anzByte; anzByte = 0;
         usb_serial_putchar(0x0D);
         usb_serial_putchar(0x0A);
         // return amount of received chars
         return n;
      // if we receive a DEL
      } else if (r == 0x7F) {
         // if there are already bytes in the buffer clear the last bit
         if (anzByte > 0) anzByte--;
      // all other char (no LF and no DEL)
      } else {
         // store the char into the buffer
         tempBuffer[anzByte] = r;
         // increase the counter
         anzByte++;
         // echo char
         usb_serial_putchar(r);
      }
   }
   return 0;
}
