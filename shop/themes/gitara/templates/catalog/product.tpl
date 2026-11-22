{extends file='parent:catalog/product.tpl'}

{block name='product_tabs'}
  {capture assign='productTabs'}{$smarty.block.parent}{/capture}
  {$productTabs|replace:'<li class="nav-item">':'<li class="nav-item" role="presentation">' nofilter}
{/block}
