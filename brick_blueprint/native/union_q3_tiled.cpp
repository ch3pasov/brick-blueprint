#include "clipper2/clipper.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <chrono>
#include <random>
#include <map>
using namespace std;using namespace Clipper2Lib;
int64_t parseNum(string s){bool neg=!s.empty()&&s[0]=='-';if(neg||(!s.empty()&&s[0]=='+'))s.erase(0,1);auto pos=s.find('.');string a=s.substr(0,pos),b=pos==string::npos?"":s.substr(pos+1);if(b.size()>6)throw runtime_error("precision exceeds input contract");while(b.size()<6)b+='0';int64_t v=stoll(a.empty()?"0":a)*1000000+stoll(b.empty()?"0":b);if(abs(v)>2000000000LL)throw runtime_error("coordinate out of safe range");return neg?-v:v;}
string number(int64_t v){bool neg=v<0;if(neg)v=-v;string a=to_string(v/1000000),b=to_string(v%1000000+1000000).substr(1);while(!b.empty()&&b.back()=='0')b.pop_back();return(neg?"-":"")+a+(b.empty()?"":"."+b);}
Paths64 parse(string d,int64_t q){Paths64 ps;Path64 p;size_t i=0;auto quant=[&](int64_t v){return v>=0?(v+q/2)/q*q:-((-v+q/2)/q*q);};while(i<d.size()){char c=d[i++];if(c=='Z'){p=TrimCollinear(p);if(p.size()>2)ps.push_back(p);p.clear();continue;}if(c!='M'&&c!='L')throw runtime_error("only absolute M/L/Z input supported");size_t j=d.find(',',i),k=d.find_first_of("MLZ",j+1);if(j==string::npos||k==string::npos)throw runtime_error("bad coordinate");Point64 v(quant(parseNum(d.substr(i,j-i))),quant(parseNum(d.substr(j+1,k-j-1))));if(p.empty()||p.back()!=v)p.push_back(v);i=k;}return ps;}
int winding(const Paths64&ps,long double x,long double y){int n=0;for(auto&p:ps){if(p.empty())continue;auto a=p.back();for(auto b:p){long double z=(long double)(b.x-a.x)*(y-a.y)-(long double)(b.y-a.y)*(x-a.x);if(a.y<=y&&b.y>y&&z>0)n++;if(a.y>y&&b.y<=y&&z<0)n--;a=b;}}return n;}
void tiledUnion(const Paths64&ps,Paths64&solution){const int64_t step=16000000;map<pair<int,int>,Paths64>tiles;
for(auto&p:ps){if(p.size()<3)continue;int64_t x0=INT64_MAX,x1=INT64_MIN,y0=INT64_MAX,y1=INT64_MIN;for(auto v:p){x0=min(x0,v.x);x1=max(x1,v.x);y0=min(y0,v.y);y1=max(y1,v.y);}int ax=floor((double)x0/step),bx=floor((double)x1/step),ay=floor((double)y0/step),by=floor((double)y1/step);for(int y=ay;y<=by;y++)for(int x=ax;x<=bx;x++){auto&dst=tiles[{x,y}];if(ax==bx&&ay==by){dst.push_back(p);continue;}auto clipped=RectClip(Rect64(x*step,y*step,(x+1)*step,(y+1)*step),p);for(auto&q:clipped)dst.push_back(std::move(q));}}
int tileIndex=0;for(auto&tile:tiles){if(tileIndex++%10==0)cerr<<"tile "<<tileIndex<<"/"<<tiles.size()<<" input paths "<<tile.second.size()<<endl;Clipper64 c;c.PreserveCollinear(false);c.AddSubject(tile.second);Paths64 local;if(!c.Execute(ClipType::Union,FillRule::NonZero,local))throw runtime_error("tile union failed");for(auto&p:local)solution.push_back(std::move(p));}}
void write_opaque_underpaint(const char* scene_file, const char* mask_file);
int main(int argc,char**argv){try{
if(argc==4 && std::string(argv[1])=="--underpaint"){write_opaque_underpaint(argv[2],argv[3]);return 0;}
if(argc!=4)return 2;ifstream in(argv[1]);ofstream out(argv[2]);int64_t quantum=stoll(argv[3]);string line;mt19937_64 rng(31051);long long totalInput=0,totalOutput=0,totalPolys=0,probes=0,diff=0;auto start=chrono::steady_clock::now();
while(getline(in,line)){auto a=line.find(" d=\"");if(a==string::npos||line.find("<path")==string::npos){out<<line<<'\n';continue;}a+=4;auto z=line.find('"',a);if(z==string::npos)throw runtime_error("unclosed d");Paths64 ps=parse(line.substr(a,z-a),quantum),solution;if(!ps.empty())tiledUnion(ps,solution);
long long ni=0,no=0;int64_t x0=INT64_MAX,x1=INT64_MIN,y0=INT64_MAX,y1=INT64_MIN;for(auto&p:ps)for(auto v:p){ni++;x0=min(x0,v.x);x1=max(x1,v.x);y0=min(y0,v.y);y1=max(y1,v.y);}for(auto&p:solution)no+=p.size();
if(ni){for(int j=0;j<100;j++){long double x=x0+(long double)(rng()%1000000000)/1000000000*(x1-x0),y=y0+(long double)(rng()%1000000000)/1000000000*(y1-y0);bool u=winding(ps,x,y)!=0,v=winding(solution,x,y)!=0;if(u!=v)diff++;probes++;}}
ostringstream d;for(auto&p:solution){for(size_t i=0;i<p.size();i++)d<<(i?'L':'M')<<number(p[i].x)<<','<<number(p[i].y);d<<'Z';}out<<line.substr(0,a)<<d.str()<<line.substr(z)<<'\n';totalInput+=ni;totalOutput+=no;totalPolys+=solution.size();cerr<<ni<<" -> "<<no<<" probes "<<probes<<" mismatches "<<diff<<'\n';}
cout<<"{\"input_vertices\":"<<totalInput<<",\"output_vertices\":"<<totalOutput<<",\"output_polygons\":"<<totalPolys<<",\"independent_winding_probes\":"<<probes<<",\"probe_mismatches\":"<<diff<<",\"coordinate_quantum_micro_px\":"<<quantum<<",\"seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"}\n";return diff?3:0;
}catch(exception&e){cerr<<e.what()<<'\n';return 1;}}
