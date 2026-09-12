declare module "smiles-drawer" {
  const SmilesDrawer: {
    Drawer: new (options:Record<string,unknown>) => { draw:(tree:unknown,target:HTMLCanvasElement,theme:string,infoOnly:boolean)=>void };
    parse:(smiles:string,success:(tree:unknown)=>void,error?:(reason:unknown)=>void)=>void;
  };
  export default SmilesDrawer;
}
