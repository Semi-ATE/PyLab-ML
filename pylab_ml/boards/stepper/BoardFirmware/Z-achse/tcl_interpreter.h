

#ifndef _TCL_INTERPRETER_H
#define _TCL_INTERPRETER_H

#define MAX_VAR_LENGTH      256
#define LED_CONFIG          pinMode(13, OUTPUT)
#define LED_ON              digitalWrite(13,HIGH)
#define LED_OFF             digitalWrite(13,LOW)
#define MAX_STRING_LENGTH   1024
#define OK                  0
#define ERROR               -1

enum LED_MODES {
    LED_STATUS,
    LED_STBY
};


/* Token type and control flow constants */
enum { TCMD, TWORD, TPART, TERROR };
enum { FERROR, FNORMAL, FRETURN, FBREAK, FAGAIN };

typedef char tcl_value_t;

/* A helper parser struct and macro (requires C99) */
struct tcl_parser {
  const char *from;
  const char *to;
  const char *start;
  const char *end;
  int q;
  int token;
};

struct tcl_var {
  tcl_value_t *name;
  tcl_value_t *value;
  struct tcl_var *next;
};

struct tcl_env {
  struct tcl_var *vars;
  struct tcl_env *parent;
};

struct tcl {
  struct tcl_env *env;
  struct tcl_cmd *cmds;
  tcl_value_t *result;
};

typedef int (*tcl_cmd_fn_t)(struct tcl *, tcl_value_t *, void *);

struct tcl_cmd {
  tcl_value_t *name;
  int arity;
  tcl_cmd_fn_t fn;
  void *arg;
  struct tcl_cmd *next;
};


#define tcl_each(s, len, skiperr)                                              \
  for (struct tcl_parser p = {NULL, NULL, (s), (s) + (len), 0, TERROR};        \
       p.start < p.end &&                                                      \
       (((p.token = tcl_next(p.start, p.end - p.start, &p.from, &p.to,         \
                             &p.q)) != TERROR) ||                              \
        (skiperr));                                                            \
       p.start = p.to)


#ifdef __cplusplus
extern "C" {
#endif
void tcl_init(struct tcl *tcl);
void parse_and_execute_command(short len);
void tcl_register(struct tcl *tcl, const char *name, tcl_cmd_fn_t fn, int arity,void *arg);
int tcl_eval(struct tcl *tcl, const char *s, size_t len);
void printLine(const char *string);
void prints(const char *string);
int16_t check_recv(void);
#ifdef __cplusplus
}
#endif

#endif // _TCL_INTERPRETER_H
